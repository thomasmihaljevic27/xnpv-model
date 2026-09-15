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

import numpy as np
import pandas as pd

import rebuild_config as C
import forecast_harness as H
import player_season_table as T
from ability_forecast import A0Production

SCRIPT_VERSION = "1.3"

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


# -- 12. the comparator is the live chain, not a simpler rule ---------------
def c12(table):
    """Every improvement figure was quoted against a benchmark that carries the
    trailing anchor flat with participation at one. The live chain has an aging
    path and exit-hazard survival, so the gap was widest exactly where those
    two do the most work."""
    import information_set as ISET
    from ability_forecast import A0Production
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
    flat = A0Production()
    flat.fit(iset.seasons, before=page)
    hs = [0, 5]
    lp = live.predict(iset, subs, hs).set_index(["career_key", "h"])
    fp = flat.predict(iset, subs, hs).set_index(["career_key", "h"])

    # The two differences that define the live chain, each asserted.
    moved = (lp.xs(5, level="h")["rate_82"] - lp.xs(0, level="h")["rate_82"]).abs().mean()
    assert moved > 1e-6, (
        "the adapter's rate does not change with the horizon, so the aging "
        "path is not engaging and it is still the flat benchmark")
    surv = lp.xs(5, level="h")["p_play"].mean()
    assert surv < 0.95, f"survival at five seasons out is {surv:.3f}, effectively one"
    flat_still = (fp.xs(5, level="h")["rate_82"] - fp.xs(0, level="h")["rate_82"]).abs().max()
    assert flat_still < 1e-9, "the flat benchmark is no longer flat"
    return (f"live chain: rate moves {moved:.3f} WAR by h5, survival {surv:.3f}; "
            f"the flat benchmark does neither")


def main() -> None:
    warnings.filterwarnings("ignore")
    C.banner("repair_checks.py", SCRIPT_VERSION)
    bd = C.OUT_DIR / "birthdates.csv"
    table = T.build(birthdate_csv=bd if bd.exists() else None, verbose=False)
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
                     ("live chain available as comparator", c12)]:
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
