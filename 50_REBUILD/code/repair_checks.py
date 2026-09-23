"""repair_checks.py -- the guards from the 2026-09-15 repair pass, run as tests.

EXPERIMENTAL, and deliberately a separate entry point. Each check here
corresponds to a defect the independent review found, and each one is written
so that it FAILS on the code as it stood before the repair. That is the point:
a guard nobody has seen fail is a guard nobody has tested.

    python 50_REBUILD/code/repair_checks.py

Checks 1 and 2 need only the vendor WAR file. Checks 3 to 6 need the age join,
so on a checkout without the confidential contract export they are reported as
skipped rather than passed.
"""
from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

import rebuild_config as C
import forecast_harness as H
import player_season_table as T
from ability_forecast import A0Production

SCRIPT_VERSION = "2.9"

PASS, FAIL, SKIP = "pass", "FAIL", "skip"
results: list[tuple[str, str, str]] = []


def check(name: str, fn) -> None:
    try:
        note = fn()
        results.append((name, PASS, note or ""))
    except AssertionError as e:
        results.append((name, FAIL, str(e)[:200]))
    except (AttributeError, TypeError, ValueError, KeyError) as e:
        # A guard that does not exist yet fails this suite rather than
        # crashing it: that is what running the checks against the
        # pre-repair code is for.
        results.append((name, FAIL, f"{e.__class__.__name__}: {str(e)[:170]}"))
    except _Skip as e:
        results.append((name, SKIP, str(e)))
    except FileNotFoundError as e:
        # A CONFIDENTIAL VENDOR FILE THIS MACHINE DOES NOT HAVE is an absent
        # environment, not an absent guard, and the docstring above has always
        # said so. It did not behave that way: the first check to reach for the
        # contract export took the whole suite down with it, so a checkout
        # without the export could not run even the checks that need nothing
        # but the WAR file. The file that was missing is named in the note, so
        # a skip can never be read as a pass.
        results.append((name, SKIP, f"missing input: {Path(str(e).splitlines()[0]).name}"))


class _Skip(Exception):
    pass


# -- 1. the season identity -------------------------------------------------
def c1(table):
    """WAR == WAR_82 * gp_share, in every season including the two shortened
    ones. Before the repair this failed by 82/70 in 2019-20 and 82/56 in
    2020-21, because the per-82 rate was taken from the already-scaled total."""
    # Computed here rather than delegated to the table builder's own
    # assertion, so that this check runs unchanged against the code as it
    # stood before the repair. A check that imports the fix cannot witness
    # the bug.
    played = table[(table["GP"] > 0) & table["WAR"].notna() & table["WAR_82"].notna()]
    sched = played["syr"].map(C.SEASON_LEN).fillna(float(C.FULL_SEASON))
    n_clip = int((played["GP"] > sched).sum())
    played = played[played["GP"] <= sched]
    ratio = (played["WAR_82"] * played["gp_share"] / played["WAR"])
    by_season = ratio.groupby(played["syr"]).median()
    off = by_season[(by_season - 1.0).abs() > 1e-9]
    assert off.empty, (
        "WAR does not equal WAR_82 * gp_share. Median reconstruction ratio by "
        "season: " + ", ".join(f"{int(y)}: {v:.6f}" for y, v in off.items()))
    return f"{len(played)} played rows, {n_clip} excluded by the games-share clip"


# -- 2. rates are on one scale across seasons -------------------------------
def c2(table):
    """The deeper half of the same defect. A rate inflated in one season is not
    comparable with the next, and the trailing anchors blend two seasons, so a
    scale break inside the window contaminates every anchor that spans it."""
    med = table[table["GP"] >= C.MIN_GP].groupby("syr")["WAR_82"].median()
    short = [y for y in C.SEASON_LEN if y in med.index]
    normal = med.drop(index=short)
    lo, hi = float(normal.min()), float(normal.max())
    for y in short:
        v = float(med.loc[y])
        assert lo * 0.75 <= v <= hi * 1.25, (
            f"the {y} median rate {v:.4f} sits outside the range of the "
            f"full-length seasons ({lo:.4f} to {hi:.4f}), which is the scale "
            "break the identity check is meant to prevent")
    return ", ".join(f"{y}: {float(med.loc[y]):.4f}" for y in short) + \
        f" against full-season {lo:.4f} to {hi:.4f}"


# -- 3. the games unit ------------------------------------------------------
def c3(_table):
    """Predicted games are converted on the outcome season's own schedule. A
    player available for all 56 games of 2020-21 used to be charged a 26-game
    error for a season he did not miss."""
    d = pd.DataFrame({"p_play": [1.0], "rate_82": [2.0], "gp_share": [1.0],
                      "season": [2020], "act_war": [2.0], "act_gp": [56.0],
                      "act_rate_82": [2.0], "act_gp_share": [1.0]})
    e = float(H._score_rows(d)["e_gp"].iloc[0])
    assert abs(e) < 1e-9, f"a fully available 2020-21 season scores {e:+.1f} games of error"
    return "a full 2020-21 season scores zero games of error"


# -- 4. no model may answer a horizon it never fitted -----------------------
def c4(table):
    """Before the repair a request for year seven returned a flat 0.6
    participation and the trailing rate, and that fabricated tail went into the
    long-contract averages and from there into the fitted price line."""
    from ability_forecast import A1Calibrated
    import information_set as ISET
    iset = ISET.build(table, ISET.decision_date_for_page(2021), t0=2021)
    subs = H.subjects_at(iset).head(20)
    if subs.empty:
        raise _Skip("no eligible subjects on the 2021 page in this checkout")
    m = A1Calibrated()
    m.fit(iset.seasons, before=2021)
    # The model's OWN range, not the class default: the fitted range is decided
    # per page from the evidence, so this page reaches further than the default
    # and asking for default+1 would be asking for a horizon it really has.
    beyond = max(m.fitted_horizons_) + 1
    try:
        m.predict(iset, subs, [beyond])
    except ValueError:
        return (f"horizon {beyond} refused; this page fitted "
                f"{min(m.fitted_horizons_)}-{max(m.fitted_horizons_)}")
    raise AssertionError(f"horizon {beyond} was answered despite never being fitted")


# -- 5. no model may answer a question it was not asked ---------------------
def c5(table):
    """The harness validated the contents of whatever frame came back and never
    that the frame answered the question, so a model returning one player for a
    page of hundreds passed every assertion and was scored on its own sample."""
    class OneRow(A0Production):
        name = "returns one player only"

        def predict(self, iset, subs, horizons):
            return super().predict(iset, subs, horizons).head(1)

    h = H.Harness(table)
    try:
        h.run(OneRow(), pages=[2021], horizons=[0, 1])
    except AssertionError:
        return "a model returning one row of the requested grid is refused"
    raise AssertionError("the one-row model was scored")


# -- 6. both reserved samples are enforced ----------------------------------
def c6(table):
    """The page seal covered forecast scoring only, so both market runners swept
    reserved start cohorts on every development run, and the page seal itself
    accepted an unseal with no reason."""
    h = H.Harness(table)
    page = C.CONFIRMATORY_PAGES[0]
    for kw in ({}, {"unseal": True, "reason": ""}):
        try:
            h.run(A0Production(), pages=[page], horizons=[0], **kw)
        except C.ConfirmatorySealBroken:
            continue
        raise AssertionError(f"page {page} was scored with {kw or 'no unseal'}")
    try:
        C.check_market_cohorts(range(2018, 2026), "repair_checks")
    except C.ConfirmatorySealBroken:
        return (f"pages {list(C.CONFIRMATORY_PAGES)} and start years "
                f"{list(C.CONFIRMATORY_START_YEARS)} both refuse")
    raise AssertionError("the reserved market cohorts were evaluated")


# -- 7. participation and production condition on the same event ------------
def c7(table):
    """The forecast is participation multiplied by production, so the two have
    to be the same event. Participation predicted a ten-game season while the
    rate and games targets were read from any season with a number in it, so a
    cameo was a played season for one half and an unplayed one for the other."""
    from ability_forecast import A1Calibrated
    # THE FULL TABLE, as the harness passes it. The anchors are filtered to
    # qualifying seasons inside _training_pairs, but the OUTCOMES are looked up
    # in the unfiltered table, which is where the cameo seasons live. Passing a
    # pre-filtered table here hides the very rows the check is looking for.
    m = A1Calibrated()
    m.fit(table, before=2021)
    pairs = m._training_pairs(table, 2021, C.FITTED_HORIZONS)
    have_rate = pairs["y_rate"].notna()
    disagree = int((have_rate & ~pairs["y_played"]).sum())
    assert not disagree, (
        f"{disagree} training pairs carry a rate target while being classified "
        "as not played. The rate and the participation event disagree.")
    # getattr, so this check still runs against a tree that predates the
    # constant and fails on the disagreement itself rather than on an import.
    ev = getattr(C, "PARTICIPATION_GP", C.MIN_GP)
    return (f"{int(have_rate.sum())} rate targets, each on a season the "
            f"participation event counts as played (>= {ev} game)")


# -- 8. returning players are asked about, and answered ---------------------
def c8(table):
    """The eligibility window says three seasons and the trailing level stopped
    at two, so a player whose only qualifying season was the oldest in the
    window was dropped. The drop fell entirely on players who missed a season
    and came back, which is the population the participation model prices."""
    import information_set as ISET
    from ability_forecast import A1Calibrated
    iset = ISET.build(table, ISET.decision_date_for_page(2021), t0=2021)
    subs = H.subjects_at(iset)
    tiers = subs["history_tier"].value_counts()
    stale = int(tiers.drop(index="current", errors="ignore").sum())
    assert stale, "no returning players were admitted on the 2021 page"
    m = A1Calibrated()
    m.fit(iset.seasons, before=2021)
    pred = m.predict(iset, subs, sorted(C.FITTED_HORIZONS))
    blank = int(pred[["rate_82", "gp_share", "p_play"]].isna().sum().sum())
    assert not blank, (
        f"{blank} missing values in the forecast: admitting the returning "
        "players has left some of them without an anchor to answer from")
    return (f"{len(subs)} subjects, {stale} on stale history, "
            f"{blank} missing values")


# -- 9. market fits are dated at the signing --------------------------------
def c9(_table):
    """The price line was fitted on contracts sharing a START year, so an
    extension signed in 2017 could be priced on the 2018 market."""
    from contract_price_model import contract_sample
    from production_currency import ProductionCurrency
    d = contract_sample()
    d["war_per_season"] = 0.0
    for col in ("length", "is_RFA", "rfa_x_war", "is_D", "one_year", "war_year1"):
        if col not in d.columns:
            d[col] = (d["length"] == 1).astype(float) if col == "one_year" else 0.0
    try:
        ProductionCurrency().fit(d, before_date=2019)
    except TypeError:
        pass
    else:
        raise AssertionError("fit() accepted a season where a date is required")
    cut = pd.Timestamp("2019-07-01")
    cur = ProductionCurrency().fit(d, before_date=cut)
    tr = d[d["signed"] < cut]
    assert tr["signed"].max() < cut
    late = int((d["signed"] >= cut).sum())
    return (f"{len(tr)} contracts signed before {cut.date()} train the line; "
            f"the {late} signed after it are out of reach")


# -- 10. the cap path, and the identity it has to satisfy -------------------
def c10(_table):
    """Dollars were built from realised ceilings with the 2025 ceiling
    substituted for later years and no discounting, so a historical valuation
    knew the flat-cap years before they were announced."""
    seen_2017 = C.cap_path("2017-07-01", [2020, 2021])
    assert seen_2017[2020] > C.CAP_CEILING[2020], (
        "a 2017 valuation still lands on the realised 2020 ceiling, so it is "
        "reading a cap freeze that had not been announced")
    # D24: with growth and discount equal, a fully extrapolated path reduces to
    # the sum of shares times one ceiling. Demonstrated, not assumed.
    assert C.CAP_GROWTH == C.DISCOUNT_RATE
    yrs = list(range(2030, 2035))              # all beyond any announcement
    path = C.cap_path("2025-07-01", yrs)
    disc = sum(path[y] / (1 + C.DISCOUNT_RATE) ** k for k, y in enumerate(yrs))
    flat = path[yrs[0]] * len(yrs)
    assert abs(disc - flat) < 1e-6 * flat, (
        f"the D24 cancellation does not hold: {disc:,.0f} against {flat:,.0f}")
    return (f"2020 ceiling seen from 2017 is {seen_2017[2020]/1e6:.1f}M against "
            f"{C.CAP_CEILING[2020]/1e6:.1f}M realised; D24 identity holds")


# -- 11. extrapolation past the fitted range is declared and bounded --------
def c11(table):
    """A contract can outrun its own page. The rule carries the last fitted
    season forward on the decay observed at the end of the range, and every
    extrapolated row says so."""
    import information_set as ISET
    from ability_forecast import A1AgingParticipationImputedNC as L
    # A STARVED AGE JOIN CANNOT EVALUATE THIS. The rule measures a decay rate
    # at the end of the fitted range, and that decay is produced by the aging
    # model, so at 69% coverage the measured ratio is noise and the check
    # reports a four-figure error that says nothing about the rule. Skipped
    # rather than failed: the environment is the cause, not the code.
    if float(table["has_age"].mean()) < C.MIN_AGE_COVERAGE:
        raise _Skip(f"age coverage {float(table['has_age'].mean()):.1%} is too "
                    "thin to measure a decay rate against")
    war = lambda x: x["p_play"] * x["rate_82"] * x["gp_share"]
    got = {6: [], 7: [], 8: []}
    for page in (2018, 2019, 2020, 2021):
        iset = ISET.build(table, ISET.decision_date_for_page(page), t0=page)
        m = L()
        m.fit(iset.seasons, before=page)
        subs = H.subjects_at(iset)
        truth = m.predict(iset, subs, [6, 7, 8]).set_index(["career_key", "h"])
        m.fitted_horizons_ = (0, 1, 2, 3, 4, 5)   # hold the page to a short range
        ex = m.predict_beyond_fit(iset, subs, list(range(9))).set_index(["career_key", "h"])
        assert ex["extrapolated"].sum() == 3 * len(subs), "extrapolated rows are not tagged"
        for h in (6, 7, 8):
            a, b = war(truth.xs(h, level="h")), war(ex.xs(h, level="h"))
            got[h].append(100 * (b.reindex(a.index) - a).mean() / a.mean())
    # The bound guards against regression and is not a claim of accuracy. The
    # rule overstates, by about 3% one season past the fitted range and about
    # 20% three past on average, and by 32% three past on the worst of these
    # four pages. That is the documented cost of pricing a long deal from an
    # early page, and it is why the rows are tagged.
    out = []
    for h in (6, 7, 8):
        mean_b, worst = float(np.mean(got[h])), max(got[h], key=abs)
        assert abs(worst) < 40, f"horizon {h} extrapolation is off by {worst:+.1f}%"
        out.append(f"h{h} {mean_b:+.1f}% mean")
    return ", ".join(out) + f", worst page {max(got[8], key=abs):+.1f}% at h8"


# -- 12. the adapter agrees with production, method by method ---------------
def c12(table):
    """The first version of this check asserted only that rates move with the
    horizon and survival falls below one. Both were true of an adapter that
    reimplemented production's anchor and skipped its negative-anchor rule, so
    the check passed while the comparator was wrong in two ways at once. It now
    compares the adapter against production's own methods, row by row."""
    import information_set as ISET
    try:
        from production_adapter import ProductionChain
    except Exception as e:                        # noqa: BLE001
        raise _Skip(f"production modules unavailable ({e.__class__.__name__})")
    page = 2021
    iset = ISET.build(table, ISET.decision_date_for_page(page), t0=page)
    subs = H.subjects_at(iset)
    try:
        live = ProductionChain()
        live.fit(iset.seasons, before=page)
    except RuntimeError as e:
        raise _Skip(str(e)[:90])
    hs = [0, 1, 5]
    pred = live.predict(iset, subs, hs).set_index(["career_key", "h"])

    proj = live.proj_
    n_neg = n_checked = 0
    for r in subs.itertuples():
        a, src = proj.anchor(r.pkey, page)
        row0 = pred.loc[(r.career_key, 0)]
        if pd.isna(a):
            assert row0["outside_production"] == 1.0, (
                f"{r.pkey}: production has no anchor, and the adapter did not "
                "flag the row as outside production")
            continue
        assert row0["outside_production"] == 0.0
        n_checked += 1
        # THE ANCHOR ITSELF, against production's own method.
        assert abs(row0["rate_82"] - a * proj.multiplier(a, 1.0, 0)) < 1e-9, (
            f"{r.pkey}: horizon-zero forecast does not equal production's "
            "anchor through its own multiplier")
        # THE NEGATIVE-ANCHOR RULE, which is locked decision D12 v3: a negative
        # anchor keeps its value at the valuation season and projects at
        # replacement afterwards.
        if a < 0:
            n_neg += 1
            for h in (1, 5):
                v = float(pred.loc[(r.career_key, h), "rate_82"])
                assert v == 0.0, (
                    f"{r.pkey}: negative anchor projects {v:.4f} at horizon "
                    f"{h}, where production requires replacement, which is 0")
    assert n_neg, "no negative anchors on this page, so the rule is untested"
    return (f"{n_checked} anchors match production's method, {n_neg} negative "
            f"anchors project to replacement, {int(pred.xs(0, level='h')['outside_production'].sum())} "
            "rows flagged outside production")


# -- 13. an extrapolated forecast does not depend on the question -----------
def c13(table):
    """The tail decay was measured between the last two REQUESTED horizons on
    the mean of the REQUESTED subjects, so the same fitted model at the same
    date gave a different answer depending on how the question was batched."""
    import information_set as ISET
    from ability_forecast import A1HingeExposure as M
    page = 2021
    iset = ISET.build(table, ISET.decision_date_for_page(page), t0=page)
    m = M()
    m.fit(iset.seasons, before=page)
    if float(table["has_age"].mean()) < C.MIN_AGE_COVERAGE:
        raise _Skip("age coverage is too thin to fit the model this check uses")
    m.fitted_horizons_ = (0, 1, 2, 3, 4, 5)       # hold the page to a short range
    subs = H.subjects_at(iset)

    def h6(hs):
        return (m.predict_beyond_fit(iset, subs, hs).query("h == 6")
                .set_index("career_key")["rate_82"])

    # THE ENDPOINT HAS TO VARY. The first version of this check compared
    # [4,5,6] with [3,5,6], which both end their fitted run at horizon five, so
    # it could not see that the decay was being applied from the last horizon
    # the CALLER requested rather than the last one the model fitted. Varying
    # the endpoint is what exposes that, and it was worth 0.505 WAR.
    base = h6([4, 5, 6])
    for hs in ([3, 5, 6], [3, 4, 6], [2, 3, 6], [6]):
        d = float((base - h6(hs).reindex(base.index)).abs().max())
        assert d < 1e-9, f"requesting {hs} moves horizon six by {d:.4f} WAR"

    one = subs.head(1)
    ck = one["career_key"].iloc[0]
    c_one = float(m.predict_beyond_fit(iset, one, [0, 1, 2, 3, 4, 5, 6])
                  .query("h == 6")["rate_82"].iloc[0])
    d2 = abs(c_one - float(base.loc[ck]))
    assert d2 < 1e-9, f"asking about one player alone moves his forecast by {d2:.4f}"
    return ("invariant to the requested endpoint, to horizon subsets including "
            "a lone extrapolated year, and to subject subsets, exactly")


# -- 14. the market target and the discount are both dated at the signing ---
def c14(_table):
    """Dating the FIT at the signing while dividing the target by the realised
    start-year ceiling leaves future cap information in the target itself, and
    discounting from the contract start makes the wait between signing and
    start free."""
    from contract_price_model import contract_sample
    from production_currency import _offset
    d = contract_sample()
    assert "cap_ceiling_at_signing" in d.columns, "the target still uses a realised ceiling"
    early = d[d["signed"].dt.year < d["start_yr"]]
    moved = (early["cap_ceiling_at_signing"]
             != early["start_yr"].map(C.CAP_CEILING)).sum()
    assert moved, "no early-signed contract has a denominator that differs from the realised one"
    # The discount origin: the same contract signed a year earlier waits a year.
    assert _offset("2017-07-01", 2019) == 2 and _offset("2018-07-01", 2019) == 1, (
        "the discount origin is still the contract start rather than the signing")
    return (f"{len(early)} early-signed contracts, {int(moved)} with a "
            "signing-dated denominator; discount origin is the signing")


# -- 15. a long contract is not dropped by the attachment interface ---------
def c15(table):
    """The forecast attachment clipped its request at horizon eight, so a term
    reaching nine was never asked about, then failed the full-term requirement
    and vanished in the join with no record. No eligible source contract
    currently reaches that far, so this was latent rather than live, which is
    exactly the kind of defect a stub can pin down and a sample cannot."""
    import contract_price_model as CPM
    from ability_forecast import BaseModel

    class Always(BaseModel):
        """Answers every requested horizon, so only the interface is on trial."""
        name = "deterministic stub"
        FITTED_HORIZONS = None

        def fit(self, table, before):
            super().fit(table, before)

        def predict(self, iset, subs, horizons):
            rows = []
            for h in sorted(int(x) for x in horizons):
                r = subs[["career_key"]].copy()
                r["h"] = h
                r["rate_82"], r["gp_share"], r["p_play"] = 1.0, 1.0, 1.0
                rows.append(r)
            return pd.concat(rows, ignore_index=True)

    real = CPM.contract_sample().iloc[:1].copy()
    if real.empty:
        raise _Skip("no contracts in the sample")
    base = real.iloc[0]
    t0 = int(base["latest_complete"]) + 1
    two = base.copy(); two["start_yr"], two["end_yr"], two["length"] = t0, t0 + 1, 2
    ten = base.copy(); ten["start_yr"], ten["end_yr"], ten["length"] = t0, t0 + 9, 10
    pair = pd.DataFrame([two, ten]).reset_index(drop=True)
    got = CPM.attach_forecasts(pair, Always, table, verbose=False)
    terms = sorted(int(x) for x in got["length"])
    assert terms == [2, 10], (
        f"attachment returned terms {terms} where a stub answered every season "
        "of both; the ten-year contract is being dropped by the interface")
    return "a ten-year term survives attachment when the model answers it"


# -- 16. one price line serves both columns of the named comparison ---------
def c16(table):
    """The named table says its two columns differ by the forecast and not the
    price line. It used to fit a currency to each forecast table separately,
    and because the tables carry different forecast regressors the two fits
    returned different coefficients, so the printed difference was a forecast
    change and a price change added together."""
    import run_player_comparison as RPC
    from contract_price_model import contract_sample, attach_forecasts
    from ability_forecast import A1HingeExposure
    try:
        from production_adapter import ProductionChain
    except Exception as e:                        # noqa: BLE001
        raise _Skip(f"production modules unavailable ({e.__class__.__name__})")
    if float(table["has_age"].mean()) < C.MIN_AGE_COVERAGE:
        raise _Skip("age coverage is too thin to attach forecasts")

    sample = contract_sample()
    dev = [y for y in sorted(sample["start_yr"].dropna().unique().astype(int))
           if y not in C.CONFIRMATORY_START_YEARS]
    sample = sample[sample["start_yr"].isin(dev)]
    # One page is enough to prove the interface: the cheapest slice that still
    # produces two priced tables for the same quarters.
    sample = sample[sample["start_yr"] == max(dev)]
    try:
        rebuilt = RPC.prep(attach_forecasts(sample, A1HingeExposure, table, verbose=False))
        live = RPC.prep(attach_forecasts(sample, ProductionChain, table, verbose=False))
    except RuntimeError as e:
        raise _Skip(str(e)[:90])
    if rebuilt.empty or live.empty:
        raise _Skip("no contracts attached on this page")

    seen: dict = {}
    real_value = RPC.ProductionCurrency.value

    def spy(self, d):
        seen.setdefault(id(self), []).append(np.asarray(self.coef_, float).copy())
        return real_value(self, d)

    RPC.ProductionCurrency.value = spy
    try:
        priced, coefs = RPC.price_on_one_currency(rebuilt, live)
    finally:
        RPC.ProductionCurrency.value = real_value

    assert coefs, "no quarter produced a fitted currency"
    # Each currency object priced both tables, so each recorded exactly one
    # coefficient vector used more than once, and never two different ones.
    for vecs in seen.values():
        for v in vecs[1:]:
            assert np.allclose(v, vecs[0], atol=0, rtol=0), (
                "one currency object priced two different coefficient vectors")
    n_both = sum(1 for v in seen.values() if len(v) > 1)
    assert n_both, (
        "no currency object was used for both forecast tables, so the two "
        "columns are not sharing a fitted price line")
    return (f"{len(coefs)} quarters fitted once each; {n_both} priced both "
            "forecasts on the identical coefficient vector")


# -- 17. an all-rejected or empty batch returns cleanly, with its reasons ----
def c17(table):
    """When every submitted contract was rejected the attachment raised a
    KeyError before publishing the rejection report it had just promised."""
    import contract_price_model as CPM
    from ability_forecast import BaseModel

    class Nobody(BaseModel):
        """Answers for nobody, so every contract must be rejected."""
        name = "answers nothing"
        FITTED_HORIZONS = None

        def fit(self, table, before):
            super().fit(table, before)

        def predict(self, iset, subs, horizons):
            return pd.DataFrame(columns=["career_key", "h", "rate_82",
                                         "gp_share", "p_play"])

    real = CPM.contract_sample()
    if real.empty:
        raise _Skip("no contracts in the sample")
    one = real.iloc[:1].copy()
    got = CPM.attach_forecasts(one, Nobody, table, verbose=False)
    assert got.empty, "a model that answers nothing still produced priced rows"
    empty = CPM.attach_forecasts(real.iloc[:0].copy(), Nobody, table, verbose=False)
    assert empty.empty, "an empty request did not return an empty result"
    return "an all-rejected batch and an empty batch both return empty rather than raising"


# --- the 2026-09-15c uncertainty pass ---------------------------------------
# These three are not repairs of a found defect. They are the guards that ship
# WITH the interval layer, written before it was believed rather than after it
# was doubted, and they are here rather than in their own file because this is
# the suite a reviewer runs.

def c18(table):
    """The mixture arithmetic, against a case whose answer is known.

    Seasons are drawn from a distribution this test chose; the same parameters
    go into the quantile function; the stated ends must come back where the
    simulated ones are. Nothing about hockey is involved, so a failure here is
    an error in the arithmetic and cannot be anything else.
    """
    import predictive_interval as PI
    PI.self_test(n=50_000, verbose=False)
    return "stated ends match the simulated ones for five player types at three levels"


def c19(table):
    """A band beside the forecast, never instead of it, and never absent.

    Two failures this rules out. One: a wrapper that moves a point forecast
    invalidates every score already recorded for the model it wraps. Two: a
    model that declines to state a band for the players it finds hard is
    scored on coverage over an easier sample than the one it was asked about
    -- the same forfeit the harness's completeness check already refuses for
    the forecast itself.
    """
    import predictive_interval as PI
    import information_set as ISET
    from ability_forecast import A1HingeExposure

    page = 2018
    iset = ISET.build(table, ISET.decision_date_for_page(page), t0=page)
    subs = H.subjects_at(iset)
    hs = (0, 2, 4)

    plain, banded = A1HingeExposure(), PI.WithIntervals(A1HingeExposure())
    plain.fit(iset.seasons, before=page)
    banded.fit(iset.seasons, before=page)
    a = plain.predict(iset, subs, hs).sort_values(["career_key", "h"])
    b = banded.predict(iset, subs, hs).sort_values(["career_key", "h"])

    assert len(a) == len(b), "the wrapper changed how many rows come back"
    for col in ("rate_82", "gp_share", "p_play"):
        d = float(np.nanmax(np.abs(a[col].to_numpy() - b[col].to_numpy())))
        assert d == 0.0, f"the wrapper moved {col} by {d:.3e}"
    assert {"lo", "hi"}.issubset(b.columns), "no band was stated at all"
    missing = int(b["lo"].isna().sum() + b["hi"].isna().sum())
    assert not missing, f"{missing} rows came back without a band"
    bad = int((b["hi"] < b["lo"]).sum())
    assert not bad, f"{bad} rows have an upper end below their lower one"
    return f"{len(b)} rows, band stated on every one, forecast unmoved"


def c20(table):
    """The band is fitted without sight of the season being valued.

    The interval layer is the first thing in this tree that reads OUTCOMES at
    fit time -- it learns how wrong the model tends to be by looking at what
    happened. That makes it the most likely place in the rebuild for a leak,
    so it gets its own check rather than relying on the one the forecast has.

    Fitting on the whole source and fitting on a source truncated at the
    decision date must produce the same spread, to the last digit.
    """
    import predictive_interval as PI
    from ability_forecast import A1HingeExposure

    page = 2018
    model = A1HingeExposure()
    model.fit(table[table["syr"] < page], before=page)

    wide = PI.SpreadModel().fit(model, table, before=page,
                                horizons=model.fitted_horizons_)
    cut = PI.SpreadModel().fit(model, table[table["syr"] < page], before=page,
                               horizons=model.fitted_horizons_)
    assert len(wide.zs_) == len(cut.zs_), (
        f"the spread learned from {len(wide.zs_)} misses with the future "
        f"present and {len(cut.zs_)} with it removed")
    d = float(np.max(np.abs(wide.zs_ - cut.zs_)))
    assert d == 0.0, f"the fitted spread moved by {d:.3e} when the future was removed"
    assert wide.scale_ == cut.scale_, "the fitted scale moved when the future was removed"
    return f"{len(cut.zs_)} replayed misses, identical with and without the future"


def c21(table):
    """The 2026-27 ceiling is used where it was known and nowhere earlier.

    An announced ceiling is worth entering only if the date it became public
    is enforced. The league and the players' association published 2025-26 and
    2026-27 together on 2025-01-31, so a valuation from the day before must
    still extrapolate 2026-27 and one from the following July must use the
    published $104.0M exactly. Extrapolation from the 2025-26 ceiling puts it
    at $98.4M, so the two answers differ by 5.4% and a filter that had quietly
    stopped working would show up here rather than in a dollar figure nobody
    could trace.

    2027-28 is deliberately absent from the table -- the $113M in circulation
    is an estimate, not a set ceiling -- so it must still be extrapolated from
    2026-27 at the growth rate on every date.
    """
    announced = C.CAP_CEILING[2026]
    assert announced == 104.0e6, f"the 2026-27 ceiling reads {announced:,.0f}"

    before = C.cap_path("2025-01-30", [2026])[2026]
    assert abs(before - announced) > 1e6, (
        "a valuation dated the day before the announcement already knew the "
        f"2026-27 ceiling ({before:,.0f})")

    after = C.cap_path("2025-07-01", [2026])[2026]
    assert after == announced, (
        f"a valuation after the announcement used {after:,.0f} rather than "
        f"the published {announced:,.0f}")

    later = C.cap_path("2026-07-01", [2027])[2027]
    grown = announced * (1.0 + C.CAP_GROWTH)
    assert abs(later - grown) < 1.0, (
        f"2027-28 came back as {later:,.0f}; it has no confirmed ceiling and "
        f"must still be grown from 2026-27 to {grown:,.0f}")
    assert 2027 not in C.CAP_CEILING, (
        "2027-28 has an entry in the ceiling table. The figure in circulation "
        "is an estimate and an estimate does not belong in a slot reserved "
        "for an announced, exogenous number.")
    return ("2026-27 at $104.0M from 2025-01-31, extrapolated before it; "
            "2027-28 still unannounced")


def c22(table):
    """The predictive distribution's mean is the point forecast it surrounds.

    Raised by the independent review of the uncertainty pass. The scaled
    misses the shape is built from do not average to zero -- they average to
    about +0.10, because the shape is right-skewed and the mean of a skewed
    distribution sits above its middle. Left uncentred, the conditional
    distribution is mu + sigma * Z with expectation mu + sigma * E[Z], so the
    band's own mean sat above the forecast column printed beside it.

    That is the failure mode this wrapper was written to prevent, arriving by
    a route the existing guards could not see. The point-forecast columns were
    untouched, so the "wrapper moves nothing" check passed. The zero-spread
    identity passed too, because it replaces the shape with zeros and an
    absent shape cannot be off centre. The simulation, which averages drawn
    paths rather than reading a column, would have taken the shifted number.

    Checked by integrating the quantile function the code actually returns,
    not by re-deriving the algebra the fix is based on.
    """
    import predictive_interval as PI
    import information_set as ISET
    from ability_forecast import A1HingeExposure

    page = 2018
    iset = ISET.build(table, ISET.decision_date_for_page(page), t0=page)
    subs = H.subjects_at(iset)
    m = PI.WithIntervals(A1HingeExposure())
    m.fit(iset.seasons, before=page)
    pred = m.predict(iset, subs, (0, 3, 5)).head(1500)

    mu = (pred["rate_82"] * pred["gp_share"]).to_numpy()
    want = pred["p_play"].to_numpy() * mu
    gaps = []
    for hz in sorted(pred["h"].unique()):
        k = (pred["h"] == hz).to_numpy()
        got = m.spread_.mean(int(hz), mu[k], pred["p_play"].to_numpy()[k])
        gaps.append(got - want[k])
    worst = float(np.abs(np.concatenate(gaps)).max())
    assert worst < 0.01, (
        f"the distribution's mean is up to {worst:.4f} wins from the forecast "
        "it is built around")

    # And the centring is not a no-op dressed up as one: the shape it was
    # applied to had a real mean, so a version that skipped it would fail the
    # line above rather than pass it by luck.
    removed = m.spread_.shape_mean_raw_
    assert abs(removed) > 0.01, (
        f"the shape was centred by only {removed:+.5f}, so this check cannot "
        "tell a centred implementation from an uncentred one")
    return (f"largest gap {worst:.2e} wins; the shape carried a mean of "
            f"{removed:+.3f} before centring")


def c23(table):
    """EVERY REGISTERED FORECAST VARIANT CAN BE FITTED AND ASKED A QUESTION.

    The independent review made this point after the component model was found
    raising AttributeError inside its own fit: the suite passed 22 checks while
    a candidate the variant register carries as live could not be run at all.
    Checks that all pass and still miss that are checks of the models somebody
    happened to use.

    So every model class in ability_forecast.py with a name of its own is
    fitted on one page and asked for the horizons it says it fitted, and the
    answer is held to the same contract the harness enforces: the complete
    requested grid, nothing missing, probabilities and shares in range. It does
    not test whether a variant is any GOOD -- that is the bake-off's job. It
    tests that it runs, which is the part nothing was testing.
    """
    import inspect
    import ability_forecast as AF
    import information_set as ISET
    from ability_forecast import BaseModel

    page = 2018
    iset = ISET.build(table, ISET.decision_date_for_page(page), t0=page)
    subs = H.subjects_at(iset)

    variants = sorted(
        (n, c) for n, c in vars(AF).items()
        if inspect.isclass(c) and issubclass(c, BaseModel) and c is not BaseModel
        and "name" in c.__dict__ and c.__dict__["name"] != "base")
    assert len(variants) >= 20, f"only {len(variants)} variants found; the sweep is not sweeping"

    broken = []
    for n, cls in variants:
        try:
            m = cls()
            m.fit(iset.seasons, before=page)
            # None means unrestricted, which is the convention _guard_horizons
            # reads and which the flat benchmark legitimately uses: it fits
            # nothing, so no horizon is outside its range.
            fitted = m.fitted_horizons_
            hs = [0, 2, 4] if fitted is None else [h for h in (0, 2, 4) if h in fitted]
            if not hs:
                broken.append(f"{n}: fitted no horizon this check could ask about")
                continue
            pred = m.predict(iset, subs, hs)
            want = {(k, h) for k in subs["career_key"] for h in hs}
            got = set(zip(pred["career_key"], pred["h"].astype(int)))
            if want != got:
                broken.append(f"{n}: answered {len(got)} of {len(want)} requested cells")
                continue
            for col in ("rate_82", "gp_share", "p_play"):
                if pred[col].isna().any():
                    broken.append(f"{n}: returned missing {col}")
                    break
            else:
                if not pred["p_play"].between(0, 1).all():
                    broken.append(f"{n}: p_play outside [0,1]")
                elif not pred["gp_share"].between(0, 1).all():
                    broken.append(f"{n}: gp_share outside [0,1]")
        except Exception as e:                                    # noqa: BLE001
            broken.append(f"{n}: {e.__class__.__name__}: {str(e)[:80]}")

    assert not broken, (f"{len(broken)} of {len(variants)} variants cannot be run: "
                        + "; ".join(broken[:4]))
    return f"all {len(variants)} registered variants fit and answer the grid on page {page}"


def c24(table):
    """The path simulation's own guards, on cases whose answers are known.

    Four things, and the last is the one the plan asks for by name.

    The copula must leave each season's distribution exactly as the interval
    layer fitted it, because that distribution is the one with measured
    coverage behind it and correlating the seasons is not licence to change it.
    The dependence it imposes must actually be the dependence asked for. The
    participation path must reproduce the model's marginal probabilities while
    making an exit absorbing, which are two requirements in tension. And with
    the spread set to nothing and participation certain, every path must be the
    point forecast -- the identity that replaces the retired k=0 one.

    Synthetic on purpose: the truth is constructed, so a failure is arithmetic
    and cannot be anything else. The identity is also checked on 300 real
    contracts by `run_npv_simulation.py`, where it comes back at exactly zero
    dollars.
    """
    import npv_simulation as SIM
    SIM.self_test(n_paths=3000)
    return "marginals, dependence, absorbing exit and the zero-spread identity all hold"


def c25(table):
    """THE RUNNER CANNOT SEE THE FUTURE, DRIVEN THROUGH THE RUNNER.

    The first version of this check built its own correctly-dated calibrator
    and compared it before and after corrupting the future. That tests the
    calibration and not the SELECTION, and the selection was where the defect
    was: the runner reached for the latest page's calibration for every
    contract. The review proved the gap by stubbing out the runner's own
    functions -- this check still passed.

    So it now runs the real consumption path. `per_season` and
    `page_dependence` produce what the runner produces, `calibration_for`
    picks as the runner picks, and the contract is priced on fixed draws.

    Three things are asserted, and the third is what gives the check teeth:

      1. more than one page is in play, or the test is vacuous
      2. corrupting every season at or after the early contract's decision
         date changes nothing it is given, and nothing it is worth
      3. the LATEST page's calibration would give a DIFFERENT answer -- so a
         revert to selecting by `max(spreads)` fails here rather than passing
         unnoticed
    """
    import numpy as np
    import npv_simulation as SIM
    from contract_price_model import contract_sample
    from run_npv_simulation import per_season, page_dependence, calibration_for

    full = contract_sample()
    batches = sorted(full["latest_complete"].dropna().unique())
    keep = [batches[1], batches[-3]]        # one early page and a later one
    sample = full[full["latest_complete"].isin(keep)]

    def consume(t):
        seasons, spreads = per_season(sample, t)
        pers, rets = page_dependence(spreads, t)
        return seasons, spreads, pers, rets

    seasons, spreads, pers, rets = consume(table)
    if len(spreads) < 2:
        raise _Skip("only one forecast page in this sample; nothing to select between")
    early = min(spreads)
    late = max(spreads)
    cid = next((c for c, v in seasons.items() if v[0] == early), None)
    if cid is None:
        raise _Skip("no contract sits on the early page")

    page, mu, sg, pp = seasons[cid]
    normals = np.random.default_rng(5).standard_normal((512, len(mu)))
    u_part = np.random.default_rng(6).random((512, len(mu)))

    def value_on(spreads_, pers_, rets_, which):
        sp, pe, rr = calibration_for(which, spreads_, pers_, rets_)
        return SIM.draw_paths(mu, sg, pp, sp.zs_, pe, 512, None,
                              r_return=rr, normals=normals, u_part=u_part)

    own = value_on(spreads, pers, rets, page)

    # 3. the check must be able to SEE a revert to latest-page selection
    latest = value_on(spreads, pers, rets, late)
    assert not np.allclose(own, latest), (
        f"pages {early} and {late} give the same paths, so this check could "
        "not tell correct selection from selecting the latest page")

    # 2. and the future must not move what the early contract is given
    bad = table.copy()
    m = (bad["syr"] >= page).to_numpy()
    idx = np.flatnonzero(m)
    perm = np.random.default_rng(7).permutation(idx)
    for col in ("WAR", "WAR_82", "GP", "gp_share"):
        v = bad[col].to_numpy().copy()
        v[idx] = v[perm]
        bad[col] = v
    seasons_b, spreads_b, pers_b, rets_b = consume(bad)
    sp_a, pe_a, rr_a = calibration_for(page, spreads, pers, rets)
    sp_b, pe_b, rr_b = calibration_for(page, spreads_b, pers_b, rets_b)
    d = float(np.max(np.abs(sp_a.zs_ - sp_b.zs_))) if len(sp_a.zs_) == len(sp_b.zs_) else np.inf
    assert d == 0.0, f"the shape the runner selected moved by {d:.3e}"
    assert (pe_a.w_perm_, pe_a.w_fade_, pe_a.phi_) == (pe_b.w_perm_, pe_b.w_fade_, pe_b.phi_), \
        "the persistence the runner selected moved"
    assert rr_a == rr_b, "the return rate the runner selected moved"
    after = value_on(spreads_b, pers_b, rets_b, page)
    gap = float(np.max(np.abs(own - after)))
    assert gap == 0.0, f"the simulated paths moved by {gap:.3e} when the future was scrambled"

    return (f"pages {early} and {late} both fitted; the {early} contract's paths are "
            f"identical with the future scrambled and differ from the {late} "
            "calibration, so a revert to latest-page selection would fail here")


def c26(table):
    """WHO OWNS CONTROL YEARS, AND WHAT THE OFFER COSTS -- BOTH DATED.

    Mechanical rules, on cases whose answers are CBA arithmetic rather than
    model output.

    The span is decided by ELIGIBILITY and nothing else. The first version
    read the export's expiry label and gave nothing to a contract marked "UFA
    no QO" -- but that label records a club declining to qualify the player
    years after the signing being valued, which is the very decision the
    stopping rule exists to make. The function no longer takes the label at
    all, so it cannot come back.

    The offer is dated twice over: the league minimum it floors at, and the
    BANDS themselves. The agreement carrying the 2026 bands was ratified in
    the summer of 2025, so a 2021 signing pricing a 2026 control year sees
    100% of a $1M salary, not 110%.
    """
    import control_years as CY
    import inspect

    assert "expiry" not in str(inspect.signature(CY.control_span)), (
        "control_span can see the expiry label again, which is an outcome of "
        "the decision it is supposed to be making")
    assert CY.control_span(2020, 2024) == [2021, 2022, 2023]
    assert CY.control_span(2020, 2021) == []            # already eligible
    assert CY.control_span(2020, float("nan")) == []

    # The age rule needs a birthdate and nothing else: 27 on 30 June.
    assert CY.ufa_year_by_age("1995-03-01") == 2022     # turns 27 before 30 June
    assert CY.ufa_year_by_age("1995-09-01") == 2023     # turns 27 after it

    sched = CY.qo_schedule(925_000, 925_000, [2023, 2024, 2025], 2021)
    assert abs(sched[0] - 971_250) < 1, sched           # 105%
    assert abs(sched[1] - 1_000_000) < 1, sched         # escalates, band cap
    assert abs(sched[2] - 1_000_000) < 1, sched
    assert abs(CY.qualifying_offer(500_000, 500_000, 2024, False)
               - 775_000) < 1                           # league-minimum floor
    old = CY.qo_schedule(1e6, 1e6, [2026], 2021, decision_date="2021-07-01")
    new = CY.qo_schedule(1e6, 1e6, [2026], 2021, decision_date="2025-08-01")
    assert abs(float(old[0]) - 1_000_000) < 1, old
    assert abs(float(new[0]) - 1_100_000) < 1, new
    return ("eligibility decides the span and the label cannot reach it; the "
            "offer escalates, floors, and switches bands only once they exist")


def c27(table):
    """A WALK-AWAY IS FINAL, IN HINDSIGHT AND IN THE POLICY.

    The right dies when the club declines, so a year that loses money is worth
    taking when the years behind it more than pay for it. On a path worth
    +5, -1, +10 a club that stops at the first loss collects 5 and one that
    holds collects 14.

    That is true of the CEILING, which is the best prefix rather than the
    myopic rule -- and it is equally true of the POLICY, which is why the
    informed rule asks whether any run of remaining seasons is worth keeping
    rather than whether the next one is. The first version fixed the ceiling
    and left the policy myopic, so part of what it reported as the value of
    deciding as you go was really the value of counting the later years.
    """
    import control_years as CY
    import numpy as np

    d = np.array([[5.0, -1.0, 10.0], [-2.0, -1.0, -1.0], [1.0, 2.0, 3.0]])
    best = CY.best_stop(d)
    assert abs(best[0] - 14.0) < 1e-9, best
    assert abs(best[1] - 0.0) < 1e-9, best
    assert abs(best[2] - 6.0) < 1e-9, best
    myopic = (CY._run_while(d > 0) * d).sum(axis=1)
    assert myopic[0] == 5.0 and best[0] > myopic[0], (myopic, best)

    # The policy, on the same shape of case: the expected second year loses
    # money and the third more than pays for it, so the club holds.
    disc = np.ones(3)
    exp = np.array([[5.0, -1.0, 10.0], [5.0, -1.0, -10.0]])
    hold = CY.best_outlook(exp, disc, 0)
    assert bool(hold[0]) and bool(hold[1])          # year one pays either way
    assert bool(CY.best_outlook(exp[:1, 1:], disc, 1)[0]), (
        "the policy walks away from a losing year the next one pays for")
    assert not bool(CY.best_outlook(exp[1:, 1:], disc, 1)[0]), (
        "the policy holds a losing year nothing pays for")

    rng = np.random.default_rng(20260917)
    x = rng.normal(size=(500, 5))
    b = CY.best_stop(x)
    for take in (np.ones_like(x), CY._run_while(x > 0)):
        assert ((take * x).sum(axis=1) <= b + 1e-9).all()
    assert (b >= -1e-12).all()
    return ("ceiling and policy both sit through a bad year to reach a good "
            "one; nothing beats the ceiling on 500 random paths")


def c28(table):
    """THE CLUB SEES WHAT IT WAS SHOWN, AND ONLY THAT.

    Three things, and the middle one is what the first version got wrong.

    It cannot see the season it is deciding about: every season from the
    decision onward is redrawn and the expectation comes back bit for bit.

    It cannot see the misses of seasons the player spent out of the league.
    Those exist inside the simulator and nobody ever observed them -- watching
    a player miss a year tells you he missed it, not how well he would have
    played. Conditioning on them was worth a decision change on 188 of 252
    contracts.

    It CAN see the misses of seasons he played, or the rule is vacuous. And
    that observation is only the same as seeing his production because the
    production shape is monotone, which is asserted rather than assumed.
    """
    import control_years as CY
    import npv_simulation as SIM
    import numpy as np

    pers = SIM.Persistence()
    pers.w_perm_, pers.w_fade_, pers.phi_ = 0.15, 0.30, 0.6
    mat = pers.matrix(5)
    rng = np.random.default_rng(11)
    g = rng.standard_normal((400, 5)) @ np.linalg.cholesky(mat).T
    shape = np.sort(rng.standard_normal(200))
    assert CY.shape_is_monotone(shape)
    assert not CY.shape_is_monotone(np.array([0.0, 1.0, 0.5]))
    played = (rng.random((400, 5)) < 0.7).astype(float)
    moved = 0
    for j in range(5):
        base, _ = CY.conditional_nodes(g, mat, j, shape, played)
        fut = g.copy()
        fut[:, j:] = rng.standard_normal(fut[:, j:].shape)
        assert float(np.abs(base - CY.conditional_nodes(
            fut, mat, j, shape, played)[0]).max()) == 0.0, (
            f"the expectation at season {j} moves when the future is redrawn")
        hid = g.copy()
        mask = played[:, :j] == 0
        if mask.any():
            blk = hid[:, :j]
            blk[mask] = rng.standard_normal(int(mask.sum()))
            hid[:, :j] = blk
            assert float(np.abs(base - CY.conditional_nodes(
                hid, mat, j, shape, played)[0]).max()) == 0.0, (
                f"the expectation at season {j} moves when the misses of "
                f"seasons he did not play are redrawn")
        if j:
            seen = g.copy()
            seen[:, :j] = rng.standard_normal(seen[:, :j].shape)
            moved += int(float(np.abs(base - CY.conditional_nodes(
                seen, mat, j, shape, played)[0]).max()) > 1e-9)
    assert moved == 4, ("the expectation ignores the seasons he played, so "
                        "the rule is not using the information it claims to")
    return ("the future and the unseen misses move nothing, bit for bit; the "
            "seasons he played move it at all four horizons")


def c29(table):
    """THE GOALIE PANEL IS THE SKATER PANEL'S SCHEMA, AND ITS ARITHMETIC HOLDS.

    The information set, the harness and the scoring are written against a
    schema rather than against skaters, so the goalie branch earns all of
    them by producing that schema -- and has to produce it correctly. The
    rate is built from the raw total before D20 so that the proration in the
    total and the schedule in the games share cancel exactly, which is the
    skater table's reason and holds here by the same arithmetic.

    Also asserted: one row per goaltender-season after a traded goaltender's
    team-halves are summed, and that the table carries goaltenders and only
    goaltenders.
    """
    import goalie_season_table as GST

    a = GST.build(verbose=False)
    need = {"pkey", "career_key", "syr", "pos", "WAR", "WAR_82", "GP",
            "gp_share", "exp_seasons", "exp_censored", "age", "has_age"}
    assert need <= set(a.columns), need - set(a.columns)
    assert (a["pos"] == "G").all()
    assert not a.duplicated(["career_key", "syr"]).any()
    # NO GOALTENDER IN THIS PANEL HAS EVER PLAYED 82 GAMES -- the busiest
    # season on record is 77 -- so the identity is asserted on the rate
    # itself rather than on a full season that does not exist. That absence
    # is the point: a goaltender's games are a role, and no role is every
    # game.
    assert int(a["GP"].max()) < C.FULL_SEASON
    plain = a[~a["syr"].isin(C.PRORATION)]
    assert np.allclose(plain["WAR_82"],
                       plain["WAR"] / plain["GP"] * C.FULL_SEASON, atol=1e-9)
    # A shortened season's total is stated on an 82-game basis, and its rate
    # is NOT prorated twice: the rate comes off the raw total.
    for yr in C.PRORATION:
        row = a[(a["syr"] == yr) & (a["GP"] > 20)].head(1)
        if len(row):
            r = row.iloc[0]
            assert abs(r["WAR_82"] - r["WAR"] / C.PRORATION[yr] / r["GP"]
                       * C.FULL_SEASON) < 1e-9, (yr, r["career_key"])
    return (f"{len(a)} goalie-seasons, {a['career_key'].nunique()} "
            f"goaltenders, schema and D20 arithmetic hold; busiest season "
            f"{int(a['GP'].max())} games")


def c30(table):
    """EVERY GOALIE CANDIDATE ANSWERS THE SAME QUESTION ON THE SAME EVIDENCE.

    Three things the bake-off rests on.

    A candidate cannot see the page it stands on: the base class asserts it,
    and the assertion is made to fire here rather than trusted.

    Every candidate shares ONE participation estimator, so a difference
    between two of them is about forecasting a goaltender and not about who
    is still in the league.

    And the participation estimator itself cannot see the future: it is built
    only from pages whose outcome is already complete before the page.
    """
    import numpy as np
    import goalie_season_table as GST
    import run_goalie_bakeoff as B

    a = GST.build(verbose=False)
    page = 2019
    past = a[a["syr"] < page]

    fired = False
    try:
        B.ProductionRule().fit(a, page)          # the whole table, future and all
    except AssertionError:
        fired = True
    assert fired, "a goalie candidate accepted seasons at or after its page"

    fits = [c().fit(past, page) for c in B.CANDIDATES]
    surv = [tuple(round(m.surv_[h], 12) for h in B.HORIZONS) for m in fits]
    assert len(set(surv)) == 1, (
        "the candidates do not share one participation estimator, so a "
        "difference between them mixes ability with who is still playing")

    # The estimator is unmoved when seasons at or after the page are changed,
    # which is the only way it could reach the future.
    rng = np.random.default_rng(5)
    poisoned = a.copy()
    m = poisoned["syr"] >= page
    poisoned.loc[m, "WAR"] = rng.normal(size=int(m.sum()))
    assert (B.survival_table(past, page)
            == B.survival_table(poisoned[poisoned["syr"] < page], page)), \
        "the participation estimator moved when the future was scrambled"
    return (f"{len(B.CANDIDATES)} candidates share one participation "
            f"estimator; the page guard fires; the estimator ignores the future")


def c31(table):
    """A BENCHMARK LABELLED "PRODUCTION" HAS TO BE PRODUCTION.

    The first goalie bake-off rebuilt production's cascade from a partial
    reading of `contract_npv.py` and called the result production's rule. It
    was missing the games filter, the strict slot rule, and the 0.650
    shrinkage target for a goaltender returning after an absence, and the
    conclusion drawn against that lookalike did not survive the real thing.

    So two things are asserted. The candidate that carries production's name
    calls production's own class, which is checked by breaking the import
    rather than by reading the code again. And the simplified cascade, which
    is kept for comparison, DISAGREES with it -- if the two ever coincided,
    one of them would be mislabelled.

    Also asserted: production's projector is dated by construction. Its
    lookup table is built over the whole file, and it still answers a page
    question with page information, which is proved by scrambling every
    season from the page onward.
    """
    import run_goalie_bakeoff as B
    import goalie_season_table as GST

    try:
        proj = B.production_projector()
    except Exception as exc:                      # noqa: BLE001 - reported
        return SKIP, (f"production's goalie projector did not import "
                      f"({type(exc).__name__}); the benchmark cannot be "
                      f"checked on this machine")
    assert proj.__class__.__name__ == "GoalieProjector", proj.__class__
    assert proj.__class__.__module__ == "contract_npv", (
        "the candidate carrying production's name is not production's class")

    page = 2019
    a = GST.build(verbose=False)
    past = a[a["syr"] < page]
    subs = pd.DataFrame({"career_key": sorted(
        past.loc[past["syr"] >= page - 3, "career_key"].unique())[:120]})
    real = B.ProductionProjector().fit(past, page).war_for(subs)
    mine = B.ProductionRule().fit(past, page).war_for(subs)
    gap = float((real - mine).abs().max())
    assert gap > 1e-6, ("the simplified cascade and production's projector "
                        "agree exactly, so one of them is mislabelled")

    # DATED BY CONSTRUCTION. The projector reads t0-1 and earlier, so a table
    # holding the future still answers the page's question.
    before = {k: proj.shrunk_projection(k, page)[0] for k in subs["career_key"]}
    rng = np.random.default_rng(3)
    keep = proj.lut.copy()
    fut = proj.lut.index.get_level_values(1) >= page
    proj.lut = proj.lut.copy()
    proj.lut[fut] = rng.normal(size=int(fut.sum()))
    after = {k: proj.shrunk_projection(k, page)[0] for k in subs["career_key"]}
    proj.lut = keep
    moved = [k for k in before
             if not (pd.isna(before[k]) and pd.isna(after[k]))
             and not np.isclose(before[k] or 0.0, after[k] or 0.0, equal_nan=True)]
    assert not moved, (f"production's projector moved on {len(moved)} "
                       f"goaltenders when seasons from the page onward were "
                       f"scrambled")
    return (f"the benchmark is production's own class, it differs from the "
            f"simplified cascade by up to {gap:.3f} WAR, and it ignores every "
            f"season from the page onward")


def c32(table):
    """ONE FORECAST IS ONE (PAGE, GOALTENDER, HORIZON), AND AN AGE TERM USES AGE.

    Two defects the first goalie run shipped, both invisible to the tests it
    came with.

    The paired bootstrap joined on goaltender and horizon and left the page
    out, so a 2015 forecast was matched against a 2021 one for the same
    goaltender: 3,683 intended pairs became 19,853 rows and the weighting
    moved toward goaltenders who appear on many pages. The pairing is now
    one-to-one and the join asserts it.

    And the candidate that claimed to age a goaltender took the INTERCEPT of
    its own regression -- the average change at the pivot age -- and applied
    it to everyone. Adding twenty years to every subject's age moved the
    forecast by exactly nothing. A candidate that says it uses age has to
    move when age moves.
    """
    import numpy as np
    import goalie_season_table as GST
    import run_goalie_bakeoff as B
    from player_season_table import birthdate_source

    # AGES ARE REQUIRED HERE, so the table is built with them: a panel with no
    # birthdates would make the age half of this check vacuously pass by
    # having nobody to age.
    bd, _ = birthdate_source()
    a = GST.build(birthdate_csv=bd, verbose=False, allow_thin_ages=True)
    page = 2019
    past = a[a["syr"] < page]

    # The pairing is one-to-one, and a frame with repeated (goalie, horizon)
    # across pages does not blow it up.
    left = pd.DataFrame({"career_key": ["a", "a", "b", "b"],
                         "page": [2015, 2016, 2015, 2016],
                         "h": [1, 1, 1, 1], "e_war": [1.0, 2.0, 3.0, 4.0]})
    right = left.copy(); right["e_war"] = [0.5, 0.5, 0.5, 0.5]
    assert 0.0 <= B.paired_bootstrap(left, right, n=50) <= 1.0

    # The age candidate moves when age moves.
    m = B.WorkloadWeightedAging().fit(past, page)
    import information_set as ISET
    import forecast_harness as H
    iset = ISET.build(a[a["syr"] < page], ISET.decision_date_for_page(page),
                      t0=page)
    subs = H.subjects_at(iset)
    subs = subs[subs["has_age"]].head(80).copy()
    assert len(subs) >= 20, ("too few aged goaltenders to test the age term; "
                             "the check would pass vacuously")
    young = m.predict(iset, subs, (0, 3, 5))
    old = subs.copy(); old["age"] = old["age"] + 20
    aged = m.predict(iset, old, (0, 3, 5))
    far = aged[aged["h"] > 0]
    gap = float((far["rate_82"].to_numpy()
                 - young[young["h"] > 0]["rate_82"].to_numpy()).__abs__().max())
    assert gap > 1e-9, ("the age candidate does not use age: twenty years "
                        "changed nothing")
    assert abs(float((aged[aged["h"] == 0]["rate_82"].to_numpy()
                      - young[young["h"] == 0]["rate_82"].to_numpy()).max())) < 1e-9, \
        "age moved the season the anchor already describes, which it must not"
    return (f"the pairing is one-to-one; twenty years of age moves the "
            f"forecast by up to {gap:.3f} and leaves h0 untouched")


def c33(table):
    """THE POOLED PRICE LINE RECOVERS A GOALIE SLOPE IT WAS GIVEN, AND IT
    CANNOT SEE A CONTRACT SIGNED AFTER THE DECISION.

    The goalie price line's whole output is one coefficient -- the difference
    in dollars per forecast win between a goaltender and a skater -- so the
    first thing to establish is that the arithmetic reading it is right. On
    synthetic contracts built with a known goalie slope, the fitted
    interaction has to come back as that slope.

    And the fit has to be dated: `fit_rolling` trains on contracts SIGNED
    before the decision, so a contract signed after it cannot move a
    coefficient. Both are asserted rather than described.
    """
    import numpy as np
    import run_goalie_price_line as GPL
    from production_currency import FEATURES

    rng = np.random.default_rng(20260918)
    n = 1200
    war = rng.gamma(2.0, 0.8, n)
    # FIRST-YEAR PRODUCTION IS DRAWN SEPARATELY AND PRICED AT NOTHING. Making
    # it a copy of the season average would put two identical regressors in
    # the line and the slope would split between them -- which is a fact about
    # collinearity, not about the fit, and it would make this check fail for
    # the wrong reason.
    war1 = rng.gamma(2.0, 0.8, n)
    is_g = (rng.random(n) < 0.25).astype(float)
    # A goaltender's win is worth HALF AGAIN what a skater's is, by
    # construction, on top of a level shift.
    sk_slope, g_extra, level = 0.010, 0.005, -0.004
    share = (0.006 + sk_slope * war + g_extra * is_g * war + level * is_g
             + rng.normal(0, 0.002, n))
    floor = np.full(n, 0.0075)
    d = pd.DataFrame({
        "war_per_season": war, "war_year1": war1, "length": 1.0,
        "is_RFA": 0.0, "rfa_x_war": 0.0, "is_D": 0.0, "one_year": 1.0,
        "is_G": is_g, "g_x_war": is_g * war,
        "cap_share": np.maximum(share, floor), "floor_share": floor,
        "signed": pd.to_datetime("2019-01-01")})
    coef, n_fit = GPL.fit_rolling(d, GPL.POOLED, "2020-01-01")
    assert coef is not None and n_fit == n
    got_sk = float(coef[1:][GPL.POOLED.index("war_per_season")])
    got_g = float(coef[1:][GPL.POOLED.index("g_x_war")])
    assert abs(got_sk - sk_slope) < 0.0015, (got_sk, sk_slope)
    assert abs(float(coef[1:][GPL.POOLED.index("war_year1")])) < 0.0015
    assert abs(got_g - g_extra) < 0.0015, (got_g, g_extra)
    # And the dollars helper adds the interaction rather than replacing it.
    cap = 80e6
    assert abs(GPL.dollars_per_win(coef, GPL.POOLED, cap)
               - got_sk * cap) < 1.0
    assert abs(GPL.dollars_per_win(coef, GPL.POOLED, cap, "g_x_war")
               - (got_sk + got_g) * cap) < 1.0

    # THE DEFINED RESPONSE moves every term the forecast enters. One more win
    # in every season moves the season average AND the first year, the
    # restricted interaction for a restricted player, and the goaltender
    # interaction for a goaltender -- and nothing else. The first version
    # reported the season-average coefficient alone as "dollars per win".
    b = coef[1:]
    base_v = (float(b[GPL.POOLED.index("war_per_season")])
              + float(b[GPL.POOLED.index("war_year1")]))
    assert abs(GPL.price_response(coef, GPL.POOLED, cap, False, False)
               - base_v * cap) < 1.0
    assert abs(GPL.price_response(coef, GPL.POOLED, cap, True, False)
               - (base_v + got_g) * cap) < 1.0
    assert abs(GPL.price_response(coef, GPL.POOLED, cap, False, True)
               - (base_v + float(b[GPL.POOLED.index("rfa_x_war")])) * cap) < 1.0
    # And the level-only specification is a real, separate line: it carries
    # the goaltender level and no goaltender slope.
    assert "is_G" in GPL.LEVEL_ONLY and "g_x_war" not in GPL.LEVEL_ONLY

    # DATED. A contract signed after the decision cannot reach the fit.
    later = d.copy()
    later["signed"] = pd.to_datetime("2021-01-01")
    later["cap_share"] = 0.05                      # wildly different price
    both = pd.concat([d, later], ignore_index=True)
    coef2, n2 = GPL.fit_rolling(both, GPL.POOLED, "2020-01-01")
    assert n2 == n, f"the fit reached {n2} contracts where {n} were signed in time"
    assert np.allclose(coef, coef2), "a contract signed after the decision moved the line"
    return (f"the fitted goalie slope is {got_g:.4f} against {g_extra:.4f} "
            f"given; the whole-path response moves every term the forecast "
            f"enters; a later signing cannot move the line")


def c34(table):
    """THE GOALIE PARTICIPATION PATH, EXERCISED RATHER THAN DESCRIBED.

    Four things, each of which the first version of this check claimed and
    did not test.

    1. THE FIT LEARNS FROM EVERY GOALTENDER, NOT THE SURVIVORS. A goaltender's
       birthdate is selected on his survival, so age is excluded and the fit
       must keep every anchor it is given: its base rate at each horizon has
       to equal those anchors' own played rate.

    2. THE FIT IGNORES THE FUTURE WHEN IT IS HANDED THE FUTURE. The first
       version scrambled future rows and then removed them before fitting, so
       both fits saw identical inputs. Here the WHOLE table, future seasons
       included, goes into the participation fit twice -- once clean, once
       with every season from the page onward scrambled -- and the
       coefficients must agree, and agree with a fit on the truncated table.
       The share model refuses a table that reaches the page.

    3. THE PREDICTIONS ARE A FITTED MODEL. On the rows it was fitted to, a
       logistic fit with an intercept reproduces the base rate; and it
       separates goaltenders rather than giving everyone one number. A
       predictor replaced by a constant 99.9% passed the first version.

    4. CONTRACT STATE IS READ AT THE DATE ASKED FOR. A deal signed on 16 July
       is visible to a question asked on 16 July and invisible to one asked on
       1 July. And the price runner asks at the signing: Jon Gillies's 2018
       contract, signed 16 July, must price its first season higher dated at
       the signing than at 1 July -- the review measured 44% against 93%.
    """
    import numpy as np
    import goalie_season_table as GST
    import run_goalie_participation as GPM
    import participation_model as PM
    from contract_source import load_contracts
    from player_season_table import birthdate_source

    bd, _ = birthdate_source()
    g = GST.build(birthdate_csv=bd, verbose=False, allow_thin_ages=True)
    page = 2019
    past = g[g["syr"] < page]
    contracts, _ = load_contracts()

    def fit(tbl):
        return PM.ParticipationModel(contracts, exclude=GPM.PART_EXCLUDE).fit(
            tbl, page, anchors_fn=GPM.goalie_anchors, horizons=GPM.HORIZONS)

    pm = fit(past)
    assert not {"age", "age_sq"} & set(pm.features), pm.features

    # 1. every anchor kept
    a = GPM.goalie_anchors(past[past["GP"] >= C.MIN_GP])
    have = set(zip(past["career_key"], past["syr"]))
    for h in GPM.HORIZONS:
        ah = a[a["t0"] + h < page]
        emp = float(np.mean([(k, t0 + h) in have
                             for k, t0 in zip(ah["career_key"], ah["t0"])]))
        assert abs(pm.base_[h] - emp) < 1e-9, (
            f"horizon {h}: base rate {pm.base_[h]:.3f} against the anchors' "
            f"own {emp:.3f} -- the fit is dropping rows")

    # 2. handed the future, it ignores it
    rng = np.random.default_rng(7)
    poisoned = g.copy()
    fut = poisoned["syr"] >= page
    poisoned.loc[fut, "GP"] = rng.integers(10, 80, int(fut.sum()))
    poisoned.loc[fut, "WAR"] = rng.normal(0, 3, int(fut.sum()))
    poisoned.loc[fut, "gp_share"] = rng.random(int(fut.sum()))
    full, full_p = fit(g), fit(poisoned)
    for h in GPM.HORIZONS:
        for other in (full, full_p):
            ca, cb = pm.coef_.get(h), other.coef_.get(h)
            assert (ca is None) == (cb is None)
            if ca is not None:
                assert np.allclose(ca, cb), f"horizon {h}: the future moved the fit"
            assert abs(pm.base_[h] - other.base_[h]) < 1e-12
    fired = False
    try:
        GPM.ShareModel().fit(g, page)
    except AssertionError:
        fired = True
    assert fired, "the share model accepted seasons at or after its page"

    # 3. the predictions are a fitted model, not a constant
    for h in GPM.HORIZONS:
        if pm.coef_.get(h) is None:
            continue
        ah = a[a["t0"] + h < page]
        pr = pm.predict(ah, h)
        assert abs(float(pr.mean()) - pm.base_[h]) < 0.02, (
            f"horizon {h}: in-sample mean prediction {pr.mean():.3f} against a "
            f"base rate of {pm.base_[h]:.3f}")
        assert float(pr.std()) > 0.02, f"horizon {h}: one number for everyone"

    # 4. contract state is dated -- synthetic first, then the real case
    syn = pd.DataFrame({
        "first_name": ["Test"], "last_name": ["Goalie"], "position": ["Goaltender"],
        "contract_end": ["2019-2020"], "length": [2],
        "signing_date": ["2018-07-16"], "contract_level": ["standard_level"],
        "signing_status": ["RFA"]})
    sm = PM.ParticipationModel(syn, exclude=GPM.PART_EXCLUDE)
    anc = pd.DataFrame({"career_key": ["test goalie"], "pkey": ["test goalie|G"],
                        "t0": [2018], "age": [np.nan], "tw_WAR": [1.0],
                        "tr_gp_share": [0.3], "exp_seasons": [2.0], "is_D": [0.0]})
    at_sign = sm._rows(anc, 0, as_of=pd.Timestamp("2018-07-16"))
    at_july = sm._rows(anc, 0, as_of=None)
    assert float(at_sign["under_contract"].iloc[0]) == 1.0
    assert float(at_july["under_contract"].iloc[0]) == 0.0
    assert float(at_july["contract_unknown"].iloc[0]) == 1.0

    import run_goalie_price_line as GPL
    from contract_price_model import contract_sample
    gs = contract_sample(("G",))
    gil = gs[(gs["last_name"].astype(str).str.lower() == "gillies")
             & (gs["signed"] == pd.Timestamp("2018-07-16"))]
    if len(gil):
        july = GPL.goalie_forecasts(gil, g, participation="model_july")
        sign = GPL.goalie_forecasts(gil, g, participation="model")
        assert len(july) and len(sign)
        pj, ps = float(july["p_first"].iloc[0]), float(sign["p_first"].iloc[0])
        assert ps > pj + 0.2, (
            f"the price runner does not read contract state at the signing: "
            f"Gillies prices at {pj:.1%} on 1 July and {ps:.1%} at the signing")
        note = f"Gillies first season {pj:.0%} at 1 July, {ps:.0%} at the signing"
    else:
        note = "the Gillies contract is not in this census"
    return ("every anchor kept; the future ignored when handed it; the "
            f"predictions are a fitted model; contract state dated -- {note}")


def c35(table):
    """NO PARTICIPATION FIT IS EVER HANDED A SINGULAR DESIGN.

    When every player the contract export knows about is also under contract
    for the season, the two contract columns are mirror images and the design
    loses a rank. The regularised fit then did something that depended on the
    machine: on one goalie fit it reported convergence with an arbitrary split
    between the columns, on another it raised and fell back to fewer features.
    That is why an independent rerun disagreed. On fifteen skater fits in the
    contract-using variants the arbitrary split reproduced the training rows
    and over-predicted participation on the page by up to fifteen points.

    Asserted: the rank rule drops the redundant column, in the fixed order,
    and leaves a full-rank design alone; the real goalie fits that collide are
    resolved the same way every time; and fitting twice gives identical
    coefficients.
    """
    import numpy as np
    import participation_model as PM
    import goalie_season_table as GST
    import run_goalie_participation as GPM
    from contract_source import load_contracts
    from player_season_table import birthdate_source

    rng = np.random.default_rng(3)
    n = 300
    uc = (rng.random(n) < 0.3).astype(float)
    d = pd.DataFrame({"level": rng.normal(size=n), "gp_share": rng.random(n),
                      "under_contract": uc, "contract_unknown": 1.0 - uc})
    use, dropped = PM._full_rank(d, ["level", "gp_share", "under_contract",
                                     "contract_unknown"])
    assert dropped == ["contract_unknown"] and "under_contract" in use, (use, dropped)
    d["contract_unknown"] = (rng.random(n) < 0.5).astype(float)
    use2, dropped2 = PM._full_rank(d, ["level", "gp_share", "under_contract",
                                       "contract_unknown"])
    assert dropped2 == [] and len(use2) == 4, "a full-rank design was altered"

    bd, _ = birthdate_source()
    g = GST.build(birthdate_csv=bd, verbose=False, allow_thin_ages=True)
    contracts, _ = load_contracts()
    page = 2019
    fits = [PM.ParticipationModel(contracts, exclude=GPM.PART_EXCLUDE).fit(
        g[g["syr"] < page], page, anchors_fn=GPM.goalie_anchors,
        horizons=GPM.HORIZONS) for _ in range(2)]
    hit = {h: v for h, v in fits[0].rank_dropped_.items() if v}
    assert hit, "no collision on the 2019 goalie page -- the check is vacuous"
    for h in hit:
        assert "contract_unknown" not in fits[0].used_[h]
        assert np.allclose(fits[0].coef_[h], fits[1].coef_[h])
    return (f"the redundant column is dropped in a fixed order, a full-rank "
            f"design is untouched, and the {len(hit)} colliding goalie fits on "
            f"the 2019 page resolve identically every time")


def c36(table):
    """THE GOALIE RATE IS A RATE, AND IT CANNOT SEE THE PAGE.

    run_goalie_rate forecasts WAR per 82 by pooling a goaltender's last three
    seasons weighted by games and recency, then shrinking toward a norm by the
    games behind it. Three things would break it silently:

      * a trailing window that reached season t0 or beyond, or reached back
        past three seasons -- asserted by scrambling every season outside the
        window and requiring identical rates;
      * pooling that averaged SEASONS rather than GAMES, which gives a 5-game
        cameo a full season's say in a rate -- asserted on a synthetic
        goaltender whose answer is known in closed form;
      * a forecast that is not a shrinkage: on a real page every subject's
        rate must lie between his own trailing rate and the norm, the fit must
        refuse a table that holds the page, and a horizon too thin to fit must
        borrow a SHORTER one.
    """
    import numpy as np
    import goalie_season_table as GST
    import run_goalie_rate as GR
    from player_season_table import birthdate_source

    bd, _ = birthdate_source()
    g = GST.build(birthdate_csv=bd, verbose=False, allow_thin_ages=True)
    t0 = 2019
    ref = GR.trailing_rates(g, [t0]).set_index("career_key")
    rng = np.random.default_rng(36)
    bad = g.copy()
    outside = ~bad["syr"].between(t0 - 3, t0 - 1)
    for c in ("WAR_82", "GP", "gp_share"):
        bad.loc[outside, c] = rng.permutation(bad.loc[outside, c].to_numpy())
    got = GR.trailing_rates(bad, [t0]).set_index("career_key").reindex(ref.index)
    assert np.allclose(got[["r_trail", "games", "s_trail"]].to_numpy(float),
                       ref[["r_trail", "games", "s_trail"]].to_numpy(float)), (
        "the trailing rate moved when seasons outside t0-3..t0-1 were scrambled")

    syn = pd.DataFrame({"career_key": ["x", "x"], "syr": [2018, 2017],
                        "GP": [60, 5], "WAR_82": [5.0, -20.0],
                        "gp_share": [60 / 82, 5 / 82]})
    r = GR.trailing_rates(syn, [2019]).iloc[0]
    d = GR.DECAY
    want = (60 * 5.0 + d * 5 * -20.0) / (60 + d * 5)
    assert abs(r["r_trail"] - want) < 1e-12, (r["r_trail"], want)
    assert abs(r["games"] - (60 + d * 5)) < 1e-12

    try:
        GR.RateModel().fit(g, t0)
        raise AssertionError("the rate model accepted a table holding the page")
    except AssertionError as e:
        if "accepted" in str(e):
            raise
    past = g[g["syr"] < t0]
    for role in (True, False):
        m = GR.RateModel(role_norm=role).fit(past, t0)
        a = GR.trailing_rates(past, [t0])
        for h in GR.HORIZONS:
            assert m.from_h_[h] <= h
            f = m.predict(a, h)
            lo = np.minimum(a["r_trail"], m.norm(a["s_trail"], h))
            hi = np.maximum(a["r_trail"], m.norm(a["s_trail"], h))
            assert ((f >= lo - 1e-9) & (f <= hi + 1e-9)).all(), (
                f"h{h}: a forecast outside [trailing rate, norm]")
    return (f"{len(ref)} goaltenders on the {t0} page, rates unmoved by every "
            f"season outside the window; games pooling exact; the fit refuses "
            f"the page; every forecast lies between his rate and the norm")


def c37(table):
    """THE FORECAST THAT IS PRICED IS THE FORECAST THAT WAS TESTED.

    The price runner's decomposed goalie forecast and the scored arm it is
    named after ("rate, flat norm, share model") once built the share of the
    schedule separately. Where the share model had a fit they agreed; where it
    did not -- the long horizons of the early pages -- each fell back its own
    way, and 435 cells differed by up to 1.6 WAR. Every other check passed,
    because none compared the consumer with the arm.

    Asserted on EVERY development page: the price runner's conditional season
    (rate x share, before participation), reached through the contract
    census's pkey join, equals the scored arm's rate_82 x gp_share for every
    goaltender both can price and every horizon from 0 to 7. Horizons 6 and 7
    must equal the arm's horizon 5 (the clamp). The check must meet at least
    one cell where the share model falls back and one where the rate borrows a
    shorter horizon, or it is not testing what failed.

    Participation is left out on purpose: the price runner dates it at each
    contract's signing, the harness at 1 July of the page, and check 34 covers
    that difference.
    """
    import numpy as np
    import forecast_harness as H
    import goalie_season_table as GST
    import run_goalie_rate as GR
    import run_goalie_price_line as PL
    from player_season_table import birthdate_source

    bd, _ = birthdate_source()
    g = GST.build(birthdate_csv=bd, verbose=False, allow_thin_ages=True)
    arm = H.Harness(g).run(GR.FlatShare(), pages=C.DEV_PAGES, horizons=GR.HORIZONS)
    arm["season"] = arm["rate_82"] * arm["gp_share"]
    arm = arm.set_index(["page", "career_key", "h"])["season"]
    cells = fallback = borrowed = clamped = 0
    worst = 0.0
    for page in C.DEV_PAGES:
        f = PL.rate_at_page(g, page)
        cs = f.conditional
        # career_key -> pkey -> career_key must come back to itself; a namesake
        # collision is not this check's question and is left out, counted.
        ck = arm.xs(page, level="page").index.get_level_values("career_key").unique()
        pk = (g[g["career_key"].isin(ck)].drop_duplicates("career_key")
              .set_index("career_key")["pkey"].reindex(ck))
        back = f.keymap.reindex(pk.to_numpy()).to_numpy()
        keep = back == np.asarray(ck)
        ck, pk = np.asarray(ck)[keep], pk.to_numpy()[keep]
        for h in range(0, 8):
            hh = min(h, max(GR.HORIZONS))
            want = arm.reindex(pd.MultiIndex.from_arrays(
                [np.full(len(ck), page), ck, np.full(len(ck), hh)])).to_numpy()
            got = f(pk, h)
            ok = np.isfinite(want)
            assert np.isfinite(got[ok]).all(), f"{page} h{h}: consumer declined a scored cell"
            d = float(np.abs(got[ok] - want[ok]).max()) if ok.any() else 0.0
            assert d < 1e-10, f"page {page} h{h}: priced forecast differs by {d:.4f} WAR"
            worst = max(worst, d)
            cells += int(ok.sum())
            clamped += int(ok.sum()) if h > hh else 0
            if cs.sm is None or cs.sm.coef_.get(hh) is None:
                fallback += int(ok.sum())
            else:
                fallback += int((~cs.anchors_.reindex(ck)["t0"].notna().to_numpy()
                                 & ok).sum())
            borrowed += int(ok.sum()) if cs.rm.from_h_[hh] != hh else 0
    assert fallback > 0, "no share-model fallback met -- the check is vacuous"
    assert borrowed > 0, "no borrowed rate horizon met -- the check is vacuous"
    return (f"{cells} page-goaltender-horizon cells, the priced forecast equal to "
            f"the scored arm (largest gap {worst:.1e}); {fallback} on the share "
            f"fallback, {borrowed} on a borrowed rate horizon, {clamped} clamped")


def c38(table):
    """A GOALIE MODEL REPLAYED ON AN EARLIER PAGE READS THAT PAGE.

    The predictive interval learns its spread by replaying the fitted model on
    earlier pages. The goalie models used to read the page, the qualifying
    seasons and the league average from the fit, so a model fitted for 2018
    and asked about 2015 would have asked production's projector about 2018 --
    whose projection reads the 2015-2017 seasons being scored. Asserted: fitted
    at 2018 and asked about 2015, the production arm's season forecast is
    production's projection AT 2015 for every subject, and it differs from the
    projection at 2018 for most of them, so the check has teeth.
    """
    import numpy as np
    import forecast_harness as H
    import information_set as ISET
    import goalie_season_table as GST
    import run_goalie_bakeoff as GB
    import run_goalie_rate as GR
    from player_season_table import birthdate_source

    bd, _ = birthdate_source()
    g = GST.build(birthdate_csv=bd, verbose=False, allow_thin_ages=True)
    fit_at, ask = 2018, 2015
    m = GR.ProdTrail().fit(g[g["syr"] < fit_at], fit_at)
    iset = ISET.build(g, ISET.decision_date_for_page(ask), t0=ask)
    subs = H.subjects_at(iset)
    pred = m.predict(iset, subs, [0])
    mu = (pred["rate_82"] * pred["gp_share"]).to_numpy()
    proj = GB.production_projector()
    league = float(iset.seasons.loc[(iset.seasons["syr"] < ask)
                                    & (iset.seasons["GP"] >= C.MIN_GP), "WAR"].mean())
    at_ask = np.array([(lambda v: league if v is None else float(v))(
        proj.shrunk_projection(k, ask)[0]) for k in subs["career_key"]])
    at_fit = np.array([(lambda v: np.nan if v is None else float(v))(
        proj.shrunk_projection(k, fit_at)[0]) for k in subs["career_key"]])
    assert np.allclose(mu, at_ask, atol=1e-9), "the replay is not reading its own page"
    differ = np.nanmean(np.abs(at_fit - at_ask) > 1e-6)
    assert differ > 0.5, "the two pages agree anyway -- the check is vacuous"
    return (f"fitted at {fit_at}, asked about {ask}: all {len(subs)} forecasts are "
            f"production's projection at {ask}; {differ:.0%} would differ at {fit_at}")


def c39(table):
    """THE PERSISTENCE FIT RETURNS A CURVE IT SCORED.

    The fit of how much of a miss persists searched its decay rate on the
    error of an UNCONSTRAINED fit and clipped the winner's weights afterwards,
    so it could return a curve the search never scored. On the goalie 2018 page
    it turned observed correlations of 0.25, 0.21 and 0.06 into 0.95 at one
    season. Asserted on that shape: the weights are non-negative and sum to at
    most one, the returned curve's error is the smallest over the search, and
    the one-season value sits near the observed one. And on a curve the
    constraints do not bind, the fit is the unconstrained one.
    """
    import numpy as np
    import npv_simulation as SIM

    gaps = np.array([1.0, 2.0, 3.0])
    y = np.array([0.249, 0.205, 0.058])            # the goalie 2018 page, observed
    P = SIM.Persistence()._fit_curve(gaps, y)
    assert P.w_perm_ >= 0 and P.w_fade_ >= 0 and P.w_perm_ + P.w_fade_ <= 1 + 1e-12
    curve = P.w_perm_ + P.w_fade_ * P.phi_ ** gaps
    assert abs(float(((curve - y) ** 2).sum()) - P.sse_) < 1e-12, (
        "the returned curve is not the one the search scored")
    assert abs(float(P.rho(1)) - y[0]) < 0.1, (
        f"one-season persistence {float(P.rho(1)):.3f} against {y[0]:.3f} observed")
    # NOT VACUOUS: the old recipe -- unconstrained search, clip the winner --
    # goes badly wrong on exactly this curve.
    best = None
    for phi in np.linspace(0.05, 0.95, 91):
        X = np.column_stack([np.ones(3), phi ** gaps])
        c, *_ = np.linalg.lstsq(X, y, rcond=None)
        e = float(((X @ c - y) ** 2).sum())
        if best is None or e < best[0]:
            best = (e, phi, c)
    _, phi_old, c_old = best
    wp = float(np.clip(c_old[0], 0, 1)); wf = float(np.clip(c_old[1], 0, 1 - wp))
    old_rho1 = wp + wf * phi_old
    assert old_rho1 > 0.5, "the old recipe was fine here -- the check is vacuous"
    # And where the constraints do not bind, the answer is the unconstrained one.
    y2 = 0.2 + 0.3 * 0.5 ** gaps
    Q = SIM.Persistence()._fit_curve(gaps, y2)
    assert abs(float(Q.rho(1)) - 0.35) < 1e-3 and Q.sse_ < 1e-6
    return (f"on the goalie 2018 curve the fit returns {float(P.rho(1)):.3f} at one season "
            f"against {y[0]:.3f} observed (the old recipe gave {old_rho1:.2f}); "
            f"weights in bounds; an unconstrained curve is recovered exactly")


def c40(table):
    """A CALIBRATED FORECAST WITH A LUMP FAILS THE NAIVE COVERAGE TEST, AND
    PASSES THE ONE USED INSTEAD.

    Built so the right answer is known: the forecast and the outcomes come from
    the SAME distribution, a contract value floored at the league minimum (a
    lump at one value) and a season that is zero when he does not play (a lump
    in the middle). Counting outcomes inside the 10th-90th percentile interval
    must come out well above 80% here -- which is what the goalie runner once
    read as "too wide". The randomized PIT must put 80% +- 2 points in its
    central 80%, and the interval's coverage of outcomes must match its coverage
    of the model's own draws. Both lumps are exercised: the contract floor with
    `randomized_pit`, the season zero with `mixture_pit`.
    """
    import numpy as np
    import predictive_interval as PI

    rng = np.random.default_rng(40)
    n_c, n_draw = 3000, 1500
    naive, pit, own = [], [], []
    for i in range(n_c):
        loc = rng.normal(0.0, 1.0)
        draws = np.maximum(rng.normal(loc, 1.0, n_draw), 0.0)      # floored at 0
        y = max(rng.normal(loc, 1.0), 0.0)                          # same law
        q10, q90 = np.percentile(draws, [10, 90])
        naive.append(q10 <= y <= q90)
        own.append(np.mean((draws >= q10) & (draws <= q90)))
        pit.append(PI.randomized_pit(draws, y, rng.random()))
    naive, own, pit = np.mean(naive), np.mean(own), np.array(pit)
    assert naive > 0.85, f"the lump did not inflate naive coverage ({naive:.3f}) -- vacuous"
    assert abs(np.mean((pit >= 0.1) & (pit <= 0.9)) - 0.80) < 0.02, "PIT not uniform"
    # The central share alone can come out near 80% by accident -- a PIT that
    # does not randomize across the lump does -- so the whole histogram and the
    # mean are held too. Unrandomized, the mean is about 0.67 and one decile
    # is off by about ten points.
    hist = np.histogram(pit, bins=10, range=(0, 1))[0] / len(pit)
    assert abs(pit.mean() - 0.5) < 0.02 and np.abs(hist - 0.1).max() < 0.025, (
        f"PIT not uniform: mean {pit.mean():.3f}, worst decile off by "
        f"{np.abs(hist - 0.1).max():.3f}")
    assert abs(naive - own) < 0.02, "coverage does not match the model's own draws"

    # the season mixture: lump at zero in the MIDDLE of a continuous shape
    zs = np.sort(rng.standard_normal(4001)); zs = zs - zs.mean()
    m = 20000
    p_play = rng.uniform(0.3, 0.95, m)
    mu = rng.normal(1.0, 1.0, m); sigma = rng.uniform(0.5, 1.5, m)
    plays = rng.random(m) < p_play
    y = np.where(plays, mu + sigma * np.interp(rng.random(m), np.linspace(0, 1, len(zs)), zs), 0.0)
    q10 = PI.mixture_quantile(0.1, p_play, mu, sigma, zs)
    q90 = PI.mixture_quantile(0.9, p_play, mu, sigma, zs)
    naive_s = np.mean((y >= q10) & (y <= q90))
    pits = PI.mixture_pit(y, p_play, mu, sigma, zs, rng.random(m))
    assert naive_s > 0.83, f"the zero lump did not inflate naive coverage ({naive_s:.3f})"
    assert abs(np.mean((pits >= 0.1) & (pits <= 0.9)) - 0.80) < 0.015, "mixture PIT not uniform"
    hs = np.histogram(pits, bins=10, range=(0, 1))[0] / len(pits)
    assert abs(pits.mean() - 0.5) < 0.01 and np.abs(hs - 0.1).max() < 0.012, (
        f"mixture PIT not uniform: mean {pits.mean():.3f}, worst decile off by "
        f"{np.abs(hs - 0.1).max():.3f}")
    return (f"calibrated by construction: naive 80% coverage {100 * naive:.1f}% (floor) and "
            f"{100 * naive_s:.1f}% (zero), randomized PIT central share "
            f"{100 * np.mean((pit >= 0.1) & (pit <= 0.9)):.1f}% and "
            f"{100 * np.mean((pits >= 0.1) & (pits <= 0.9)):.1f}%")


def c41(table):
    """CONTRACT STATE IS READ ONLY WHERE THE EXPORT CAN SEE IT.

    The contract export is a snapshot: every contract in it ends in or after
    its earliest end year. So "the export knows this player" is survival on an
    early page, and the goalie participation model learned it -- predicting
    retired goaltenders near-certain to play. The candidate definition
    (`contract_state="observable"`) states contract state only for seasons from
    that year on, where any covering contract must be in the export.

    Asserted: the coverage year is the export's own earliest end year; before
    it, every row -- known player or not -- reads not-observable and not under
    contract; from it on, no row is "unknown" and `under_contract` is the true
    state. Not vacuous: under the old definition the same rows still separate
    a player the export knows from one it does not.
    """
    import numpy as np
    from participation_model import ParticipationModel, contract_spans
    from contract_source import load_contracts

    contracts, _ = load_contracts()
    spans = contract_spans(contracts)
    first = int(spans["end_yr"].min())
    obs = ParticipationModel(contracts, contract_state="observable")
    old = ParticipationModel(contracts, contract_state="as_known")
    assert obs.coverage_from_ == first
    known = spans.loc[spans["pkey"].str.endswith("|G"), "pkey"].iloc[0]
    rows = []
    for k in (known, "nobody at all|G"):
        for t0 in (first - 6, first - 2, first + 2):
            rows.append({"career_key": k, "pkey": k, "t0": t0, "age": 30.0,
                         "tw_WAR": 1.0, "tr_gp_share": 0.5, "exp_seasons": 5.0,
                         "is_D": 0.0})
    a = pd.DataFrame(rows)
    for h in (0, 3):
        r = obs._rows(a, h)
        pre = r["season"] < first
        assert (r.loc[pre, "contract_unknown"] == 1).all() and (r.loc[pre, "under_contract"] == 0).all()
        assert (r.loc[~pre, "contract_unknown"] == 0).all()
        truth = old._rows(a, h)["under_contract"]
        assert np.array_equal(r.loc[~pre, "under_contract"], truth[~pre]), \
            "from the coverage year, under_contract must be the true state"
        # the old definition separates known from unknown players on the same rows
        o = old._rows(a, h)
        assert o.groupby("pkey")["contract_unknown"].mean().nunique() > 1, "vacuous"
    return (f"export snapshot from {first}: before it every row is not-observable, "
            f"from it no row is unknown and contract state is the true one; the old "
            f"definition still separates known from unknown players")


def main() -> None:
    warnings.filterwarnings("ignore")
    C.banner("repair_checks.py", SCRIPT_VERSION)
    bd = C.OUT_DIR / "birthdates.csv"
    # allow_thin_ages, deliberately. The coverage guard exists to stop a
    # SILENT degraded run, and this suite is the tool you reach for to find out
    # what state the tree is in. Letting the guard abort it would mean the
    # diagnostic refused to start on exactly the checkout most in need of a
    # diagnosis. The coverage is reported instead, and the checks that depend
    # on a full age join say so for themselves.
    table = T.build(birthdate_csv=bd if bd.exists() else None, verbose=False,
                    allow_thin_ages=True)
    cov = float(table["has_age"].mean())
    if cov and cov < C.MIN_AGE_COVERAGE:
        C.log(f"  AGE COVERAGE IS {cov:.1%}, below the {C.MIN_AGE_COVERAGE:.0%} the")
        C.log("  season table normally requires. The Elite Prospects birthdate file")
        C.log("  is missing. Age-dependent results below are degraded, not wrong.")
        C.log("")
    if not int(table["has_age"].sum()):
        C.log("  NO AGE COVERAGE in this checkout: the birthdate join needs the")
        C.log("  confidential contract export. Age-dependent checks will skip.")
    C.log("")

    for name, fn in [("season identity", c1), ("rate scale across seasons", c2),
                     ("games unit", c3), ("unfitted horizons refused", c4),
                     ("incomplete predictions refused", c5),
                     ("reserved samples enforced", c6),
                     ("one participation event", c7),
                     ("returning players answered", c8),
                     ("market fits dated at signing", c9),
                     ("cap path and the D24 identity", c10),
                     ("extrapolation declared and bounded", c11),
                     ("adapter matches production", c12),
                     ("extrapolation invariant to the query", c13),
                     ("market target and discount dated at signing", c14),
                     ("long terms survive attachment", c15),
                     ("one price line for both columns", c16),
                     ("empty and all-rejected batches", c17),
                     ("interval arithmetic", c18),
                     ("a band on every row, forecast unmoved", c19),
                     ("the band cannot see the future", c20),
                     ("the 2026-27 ceiling", c21),
                     ("the distribution's mean is the forecast", c22),
                     ("every registered variant runs", c23),
                     ("the path simulation's guards", c24),
                     ("the simulation cannot see the future", c25),
                     ("control years: eligibility and the dated offer", c26),
                     ("a walk-away is final, in ceiling and policy", c27),
                     ("the club sees what it was shown, and only that", c28),
                     ("the goalie panel's schema and arithmetic", c29),
                     ("every goalie candidate answers the same question", c30),
                     ("the production benchmark is production", c31),
                     ("one forecast per page, and age that uses age", c32),
                     ("the pooled price line reads its own goalie slope", c33),
                     ("goalie participation, exercised end to end", c34),
                     ("no participation fit sees a singular design", c35),
                     ("the goalie rate is a rate, and cannot see the page", c36),
                     ("the forecast priced is the forecast tested", c37),
                     ("a replayed goalie model reads its own page", c38),
                     ("the persistence fit returns a curve it scored", c39),
                     ("a calibrated forecast with a lump passes the PIT", c40),
                     ("contract state read only where the export can see it", c41)]:
        check(name, lambda fn=fn: fn(table))

    width = max(len(n) for n, _, _ in results)
    for name, status, note in results:
        C.log(f"  {status:<5} {name:<{width}}  {note}")
    bad = [n for n, s, _ in results if s == FAIL]
    C.log("")
    C.log(f"  {sum(s == PASS for _, s, _ in results)} passed, "
          f"{sum(s == SKIP for _, s, _ in results)} skipped, {len(bad)} failed")
    if bad:
        raise SystemExit(f"failed: {bad}")


if __name__ == "__main__":
    main()
