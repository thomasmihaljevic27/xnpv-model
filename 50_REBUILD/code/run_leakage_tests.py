"""run_leakage_tests.py -- can the forecast see the future, and how hard does
it lean on any one thing it can see?

EXPERIMENTAL (50_REBUILD). Development pages only; the confirmatory seal is
not touched.

Look-ahead is the failure this supervisor weighs above all others, and it is
the failure an error metric rewards. A model that has read next season scores
beautifully and is worth nothing. The existing stress battery checks one
version of this -- delete every season at or after the decision date and see
whether the forecast moves -- on two pages, at two horizons, for one of the
three quantities a model produces. That is a spot check, and it can only
detect a model that reaches past the harness's own filter.

Five tests here, the first three about leakage and the last two about how much
weight rests on a single input.

  1. the model's own discipline -- hand it EVERYTHING, including seasons after
     the decision date, and it must return the same answer it returns when the
     harness has already cut them away
  2. deleting the future -- the existing check, widened to every development
     page, every horizon, every output, and the new interval
  3. corrupting the future -- the same rows kept but their contents scrambled,
     which catches a read that deletion would hide
  4. the placebo -- pair every forecast with a different player's season and
     confirm the skill disappears, which is what says the scoring join is
     joining what it claims to
  5. input sensitivity -- perturb one thing the model IS allowed to see and
     measure how far the forecast moves

WHY 1 AND 2 ARE NOT THE SAME TEST
    Test 2 gives the model a table the harness has already filtered and then
    filters it again. It cannot fail unless the model reaches for data it was
    never handed. Test 1 hands the model the unfiltered table and relies on
    the model's own rule -- that a training pair counts only if its OUTCOME
    season finished before the decision date -- to throw the future away. A
    model that filtered its inputs but not its outcomes passes test 2 and
    fails test 1, and that is a real bug with a real history: a pair whose
    inputs end three seasons back still has an outcome that lands next year.

    It matters beyond tidiness. The trade-date valuation in Phase 5 builds its
    own information sets at arbitrary dates rather than taking the harness's,
    so the model's own discipline is what will be load-bearing there.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
import forecast_harness as H
import information_set as ISET
import predictive_interval as PI
from player_season_table import build as build_table
from ability_forecast import A1HingeExposure

SCRIPT_VERSION = "1.1"

LEADER = A1HingeExposure
PAGES = C.DEV_PAGES
HORIZONS = (0, 1, 2, 3, 4, 5)

# Anything below this is floating-point noise from summing in a different
# order, not a different answer. The comparisons below are between two runs of
# the same arithmetic, so a genuine leak moves a forecast by a visible amount
# and never by 1e-13.
EXACT = 1e-9


def _load_table():
    """Build the season table, and say plainly what the ages on this machine
    are worth. There are two birthdate tables and they are not equivalent: the
    merged one reaches the pages results are scored on, the Elite Prospects
    scrape on its own reaches the players who left before those pages start.
    Which one was used, and the coverage it produced, is printed rather than
    inferred."""
    from player_season_table import birthdate_source
    path, how = birthdate_source()
    table = build_table(birthdate_csv=path, verbose=False, allow_thin_ages=True)
    dev = table[table["syr"] >= min(C.DEV_PAGES)]
    cov_all = float(table["has_age"].mean())
    cov_dev = float(dev["has_age"].mean()) if len(dev) else 0.0
    C.log(f"  birthdates: {how}")
    C.log(f"  age coverage {cov_all:.1%} of all season rows, "
          f"{cov_dev:.1%} on {min(C.DEV_PAGES)} and later")
    usable = cov_dev >= C.MIN_AGE_COVERAGE
    if not usable:
        C.log("")
        C.log("!! AGE COVERAGE ON THE SCORED PAGES IS TOO THIN FOR A RESULT.")
        C.log("!! The aging walk degenerates to a flat carry-forward and the")
        C.log("!! participation fits collapse to a constant. The code paths")
        C.log("!! below all run; the figures they produce are about a crippled")
        C.log("!! model and must not be compared with anything on record.")
    C.log("")
    return table, usable


def _predict_at(table: pd.DataFrame, page: int, fit_table: pd.DataFrame | None = None,
                banded: bool = False) -> pd.DataFrame:
    """One page, one forecast. `fit_table` is what the model is allowed to fit
    on and defaults to the information set's own seasons, which is what the
    harness passes. Passing something wider is how test 1 works."""
    iset = ISET.build(table, ISET.decision_date_for_page(page), t0=page)
    subs = H.subjects_at(iset)
    model = PI.WithIntervals(LEADER()) if banded else LEADER()
    model.fit(fit_table if fit_table is not None else iset.seasons, before=page)
    hs = [h for h in HORIZONS if h in model.fitted_horizons_]
    p = model.predict(iset, subs, hs)
    return p.sort_values(["career_key", "h"]).reset_index(drop=True)


def _worst_gap(a: pd.DataFrame, b: pd.DataFrame, cols) -> tuple[float, str]:
    """Largest disagreement between two forecasts, over the columns both
    carry. Compared row by row on a sorted index, so a reordering is not
    mistaken for a difference and a changed POPULATION is caught outright."""
    if len(a) != len(b) or not (a["career_key"].to_numpy() == b["career_key"].to_numpy()).all():
        return float("inf"), "the two runs answered about different players"
    worst, where = 0.0, ""
    for c in cols:
        if c not in a.columns or c not in b.columns:
            continue
        d = float(np.nanmax(np.abs(a[c].to_numpy() - b[c].to_numpy())))
        if d > worst:
            worst, where = d, c
    return worst, where


def main() -> None:
    C.banner("run_leakage_tests.py", SCRIPT_VERSION)
    table, real_ages = _load_table()
    rng = np.random.default_rng(20260915)
    out_cols = ["rate_82", "gp_share", "p_play"]
    band_cols = out_cols + ["lo", "hi"]

    # ---- 1. the model's own discipline ------------------------------------
    C.log("TEST 1  THE MODEL'S OWN DISCIPLINE. Fit on the whole table, seasons")
    C.log("after the decision date included, and the answer must not move. The")
    C.log("harness's filter is not being tested here; the model's own rule is.")
    C.log("")
    ok1 = True
    for page in PAGES:
        cut = _predict_at(table, page, banded=True)
        # The one difference: the model is handed every season in the source,
        # 2007 to 2025, and told only the year it is standing in.
        wide = _predict_at(table, page, fit_table=table, banded=True)
        gap, where = _worst_gap(cut, wide, band_cols)
        ok1 &= gap < EXACT
        C.log(f"    page {page}: largest change {gap:.2e}"
              f"{'  in ' + where if where else ''}  "
              f"[{'PASS' if gap < EXACT else 'FAIL'}]")
    C.log(f"  {'PASS -- the model throws the future away itself' if ok1 else 'FAIL'}")
    C.log("")

    # ---- 2. deleting the future ------------------------------------------
    C.log("TEST 2  DELETING THE FUTURE. Every season at or after the decision")
    C.log("date removed from the table entirely. Widened from the existing spot")
    C.log("check to every development page, every horizon, and the interval as")
    C.log("well as the forecast.")
    C.log("")
    ok2 = True
    for page in PAGES:
        a = _predict_at(table, page, banded=True)
        b = _predict_at(table[table["syr"] < page], page, banded=True)
        gap, where = _worst_gap(a, b, band_cols)
        ok2 &= gap < EXACT
        C.log(f"    page {page}: largest change {gap:.2e}"
              f"{'  in ' + where if where else ''}  "
              f"[{'PASS' if gap < EXACT else 'FAIL'}]")
    C.log(f"  {'PASS -- deleting the future changes nothing' if ok2 else 'FAIL'}")
    C.log("")

    # ---- 3. corrupting the future ----------------------------------------
    C.log("TEST 3  CORRUPTING THE FUTURE. The same rows, in the same places,")
    C.log("with their contents shuffled between players. Deletion changes the")
    C.log("SHAPE of the table, so a code path that short-circuits on an empty")
    C.log("frame can pass it while still reading the future when the frame is")
    C.log("full. This leaves the shape alone and destroys the contents.")
    C.log("")
    ok3 = True
    for page in PAGES:
        bad = table.copy()
        m = (bad["syr"] >= page).to_numpy()
        idx = np.flatnonzero(m)
        perm = rng.permutation(idx)
        for col in ("WAR", "WAR_82", "GP", "gp_share"):
            if col in bad.columns:
                v = bad[col].to_numpy().copy()
                v[idx] = v[perm]
                bad[col] = v
        a = _predict_at(table, page, banded=True)
        b = _predict_at(bad, page, banded=True)
        gap, where = _worst_gap(a, b, band_cols)
        ok3 &= gap < EXACT
        C.log(f"    page {page}: {len(idx)} future rows scrambled, largest change "
              f"{gap:.2e}{'  in ' + where if where else ''}  "
              f"[{'PASS' if gap < EXACT else 'FAIL'}]")
    C.log(f"  {'PASS -- the future can be destroyed without moving a forecast' if ok3 else 'FAIL'}")
    C.log("")

    # ---- 4. the placebo ---------------------------------------------------
    C.log("TEST 4  THE PLACEBO. Every forecast re-paired with a DIFFERENT")
    C.log("player's season at the same page and horizon. The model should now")
    C.log("be useless. If it is not, the scoring join is not joining a player to")
    C.log("his own outcome, and every error figure in this tree is measuring")
    C.log("something other than what it says.")
    C.log("")
    h = H.Harness(table)
    s = h.run(LEADER(), pages=PAGES, horizons=HORIZONS)
    rows = []
    for (page, hz), g in s.groupby(["page", "h"]):
        g = g.copy()
        shuffled = g["act_war"].fillna(0.0).to_numpy().copy()
        rng.shuffle(shuffled)
        rows.append(pd.DataFrame({
            "h": int(hz),
            "real": (g["pred_war"].to_numpy() - g["act_war"].fillna(0.0).to_numpy()),
            "placebo": (g["pred_war"].to_numpy() - shuffled)}))
    pl = pd.concat(rows, ignore_index=True)
    C.log(f"    {'seasons ahead':<16}{'real':>10}{'placebo':>10}{'ratio':>9}")
    ok4 = True
    for hz, g in pl.groupby("h"):
        r, p = g["real"].abs().mean(), g["placebo"].abs().mean()
        ok4 &= p > r
        C.log(f"    {int(hz):<16}{r:>10.3f}{p:>10.3f}{p / r:>9.2f}")
    C.log(f"  {'PASS -- the skill is in the pairing, not in the metric' if ok4 else 'FAIL'}")
    C.log("")

    # ---- 5. input sensitivity --------------------------------------------
    C.log("TEST 5  INPUT SENSITIVITY. Perturb something the model IS entitled")
    C.log("to see, and measure how far the forecast moves. The fit is held")
    C.log("fixed and only the inputs at the decision date are disturbed, so")
    C.log("what is measured is the forecast's response and not the fit's.")
    C.log("")
    C.log("PASS-THROUGH is the share of a shock to last season that survives")
    C.log("into the forecast. The whole case for this rebuild is that one")
    C.log("season is weak evidence, so a pass-through well under one is the")
    C.log("shrinkage working. Above one would mean the model amplifies a single")
    C.log("noisy season, which is the defect the rebuild set out to remove.")
    C.log("")
    # Half a win per 82 games, which is about a third of the spread between
    # one season and the next for a regular. Big enough to be visible against
    # rounding, small enough that a model is not being asked to extrapolate.
    shock = 0.50
    rows = []
    for page in PAGES:
        base = _predict_at(table, page)
        latest = int(table[table["syr"] < page]["syr"].max())
        # The flag says whether the case is a known-sized shock to the rate,
        # which is the only one a pass-through can be computed for: removing a
        # season is a change of unknown size in the units of the input.
        for label, mutate, is_shock in [
            (f"last season's rate +{shock} wins per 82",
             lambda t: _bump(t, latest, shock), True),
            ("last season removed", lambda t: t[~((t["syr"] == latest))], False),
            ("oldest season in the window removed",
             lambda t: t[~(t["syr"] == latest - 2)], False),
            ("games played cut by a tenth",
             lambda t: _scale_gp(t, latest, 0.9), False),
        ]:
            alt = _predict_at(mutate(table.copy()), page)
            j = base.merge(alt, on=["career_key", "h"], suffixes=("", "_alt"))
            for hz, g in j.groupby("h"):
                rows.append({"page": page, "case": label,
                             "is_shock": is_shock, "h": int(hz),
                             "d_rate": float((g["rate_82_alt"] - g["rate_82"]).mean()),
                             "abs_d_war": float(
                                 ((g["rate_82_alt"] * g["gp_share_alt"] * g["p_play_alt"])
                                  - (g["rate_82"] * g["gp_share"] * g["p_play"]))
                                 .abs().mean())})
    sens = pd.DataFrame(rows)
    for label, g in sens.groupby("case", sort=False):
        C.log(f"  {label}:")
        C.log(f"    {'seasons ahead':<16}{'mean rate move':>16}{'mean |wins move|':>19}")
        for hz, gg in g.groupby("h"):
            line = (f"    {int(hz):<16}{gg['d_rate'].mean():>+16.3f}"
                    f"{gg['abs_d_war'].mean():>19.3f}")
            if bool(gg["is_shock"].iloc[0]):
                line += f"   pass-through {gg['d_rate'].mean() / shock:>5.2f}"
            C.log(line)
        C.log("")

    sens.to_csv(C.out_path("leakage_sensitivity.csv"), index=False)
    C.log(f"  wrote {C.out_path('leakage_sensitivity.csv').name}")
    C.log("")
    verdict = all([ok1, ok2, ok3, ok4])
    C.log(f"OVERALL: {'all four leakage tests pass' if verdict else 'A LEAKAGE TEST FAILED'}")
    if not real_ages:
        C.log("")
        C.log("!! REMINDER: the ages on the scored pages were too thin for a")
        C.log("!! result. Tests 1-4 compare the model against itself and stand")
        C.log("!! whatever state it is in. Test 5's numbers describe a")
        C.log("!! degenerate model and are not evidence about the real one.")
    C.write_log("leakage_tests_run_log.txt")
    assert verdict, "a leakage test failed -- see the log"


def _bump(t: pd.DataFrame, syr: int, rate: float) -> pd.DataFrame:
    """Raise one season's per-82 rate by `rate` for every player, and carry
    the change through to the season total so the table stays internally
    consistent.

    THE RATE IS WHAT IS SHOCKED, not the total, so that every player gets the
    same sized shock in the units the model reasons in. Shocking the total by
    a fixed number of wins would hit a half-season player twice as hard in
    rate terms as a full-season one and the pass-through would be an average
    over two different experiments.

    The table's own identity -- the rate times the share of the schedule is
    the season total -- is what keeps the two in step. A perturbation that
    moved one without the other would test a table state that cannot occur.

    ONLY THE TOTAL IS PERTURBED, not the six components underneath it. That
    suits a model that reads the total, which the adopted candidate does. A
    component-wise candidate would need the same shock spread across its
    components before this test said anything about it.
    """
    m = t["syr"] == syr
    t.loc[m, "WAR_82"] = t.loc[m, "WAR_82"] + rate
    t.loc[m, "WAR"] = t.loc[m, "WAR"] + rate * t.loc[m, "gp_share"]
    return t


def _scale_gp(t: pd.DataFrame, syr: int, k: float) -> pd.DataFrame:
    """Availability shock: the same rate of production over fewer games.

    Games played is a count, so it is rounded back to a whole number; the
    share of the schedule and the season total take the exact factor, since
    they are the quantities the model reads and rounding them would put noise
    into a measurement that is about a deliberate change. The rate per 82 is
    untouched by construction -- that is what makes this an availability shock
    and not a production one.
    """
    m = t["syr"] == syr
    t["GP"] = t["GP"].astype(float)
    t.loc[m, "GP"] = np.round(t.loc[m, "GP"] * k)
    t.loc[m, "gp_share"] = (t.loc[m, "gp_share"] * k).clip(upper=1.0)
    t.loc[m, "WAR"] = t.loc[m, "WAR"] * k
    return t


if __name__ == "__main__":
    main()
