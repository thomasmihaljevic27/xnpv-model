"""run_uncertainty.py -- does the model know how wrong it is?

EXPERIMENTAL (50_REBUILD). Development pages only; the confirmatory seal is
not touched.

Every score this project has published for a forecast is an error: how far the
number was from what happened. That answers one question and hides another.
A model that says "1.2 wins" and is off by 0.6 is doing well if 0.6 is the
kind of miss it warned about, and badly if it claimed to be sure. The second
question is calibration of the spread, and until this run nothing in the tree
could answer it, because no model stated a range.

Six reports, in the order a reader should want them:

  1. the wrapper changes nothing -- the point forecast is bit-identical with
     and without the interval, so no score already on record moves
  2. what the spread was fitted to be
  3. coverage and width, by horizon, at three stated levels and both tails
  4. coverage by subgroup WITHIN horizon -- an average is a place for a
     failure to hide, and that applies to a band as much as to an error
  5. for an under-covered group, whether the band is too narrow or the
     forecast it is centred on is biased -- the fix is opposite in the two
     cases and the coverage number alone cannot tell them apart
  6. the fitted spread against the realized one, page by page
  6b. the distribution's mean, which must be the point forecast
  7. the zero-spread identity: with no uncertainty, the band collapses onto
     the point forecast. The plan asks the Phase 5 simulation to satisfy the
     same identity; this is that check one layer down, where it is cheap.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
import forecast_harness as H
import predictive_interval as PI
from player_season_table import build as build_table

SCRIPT_VERSION = "1.4"

# The adopted candidate, matching run_stress_tests.py. The uncertainty layer
# wraps whatever model it is given, so this is the model under test rather
# than a property of the layer.
# The adopted skater leader, from the one switch (run_npv_simulation.LEADER),
# not a class named here: a copy pinned by name is how these diagnostics kept
# testing the old leader after it changed on 2026-09-23.
from run_npv_simulation import LEADER  # noqa: E402


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


def _coverage(d: pd.DataFrame, level: float) -> pd.Series:
    """Coverage and both tails at one stated level, from the quantile columns
    the wrapper carries. Reported as three numbers, not one: a band can hold
    the right share of outcomes while being wrong at both ends, and a model
    that misses low twice as often as it misses high is telling us something
    an aggregate coverage figure cannot."""
    tail = (1 - level) / 2
    lo = d[f"q{int(round(tail * 100)):02d}"]
    hi = d[f"q{int(round((1 - tail) * 100)):02d}"]
    y = d["act_war"].fillna(0.0)
    return pd.Series({
        "n": len(d),
        "covered": float(((y >= lo) & (y <= hi)).mean()),
        "below": float((y < lo).mean()),
        "above": float((y > hi).mean()),
        "width": float((hi - lo).mean()),
    })


def main() -> None:
    C.banner("run_uncertainty.py", SCRIPT_VERSION)
    table, real_ages = _load_table()

    h = H.Harness(table)
    plain = LEADER()
    banded = PI.WithIntervals(LEADER())

    C.log("Scoring the leading model twice: once as it stands, once with a")
    C.log("stated range around every forecast.")
    C.log("")
    s_plain = h.run(plain)
    s_band = h.run(banded)

    # ---- 1. the wrapper moves nothing ------------------------------------
    C.log("REPORT 1  THE WRAPPER CHANGES NOTHING. The interval is added beside")
    C.log("the forecast, never instead of it. If this fails, every score")
    C.log("already on record for this model would have to be re-run.")
    C.log("")
    key = ["career_key", "page", "h"]
    j = s_plain.merge(s_band, on=key, suffixes=("_a", "_b"))
    worst = max(float(np.nanmax(np.abs(j[f"{c}_a"] - j[f"{c}_b"])))
                for c in ("rate_82", "gp_share", "p_play", "pred_war"))
    assert len(j) == len(s_plain) == len(s_band), "the two runs scored different rows"
    assert worst < 1e-12, f"the wrapper moved a point forecast by {worst:.3e}"
    C.log(f"  {len(j)} rows, largest change to any point forecast {worst:.1e}  [PASS]")
    C.log("")

    # ---- 2. what the spread was fitted to be ------------------------------
    C.log("REPORT 2  THE FITTED SPREAD, as it stood at the last development")
    C.log("page. The band is a straight line in the size of the forecast, so")
    C.log("it is shown at a replacement-level forecast and at two wins.")
    C.log("")
    for line in banded.spread_.report():
        C.log(line)
    ext = sorted(banded.spread_.extended_)
    if ext:
        share = float(s_band["band_extended"].mean())
        C.log(f"  {share:.1%} of scored rows carry a band extended rather than")
        C.log(f"  fitted (horizons {ext} at one or more pages).")
    C.log("")

    # ---- 3. coverage by horizon -------------------------------------------
    C.log("REPORT 3  COVERAGE AND WIDTH BY HORIZON. 'covered' should sit on the")
    C.log("stated level. Below it the model is overconfident -- the honest")
    C.log("reading is that it knows less than it says. Above it the band is")
    C.log("wider than it needs to be, which is a different kind of wrong and a")
    C.log("cheaper one. 'below' and 'above' are the two tails separately.")
    C.log("")
    rows = []
    for level in PI.REPORT_LEVELS:
        for hz, g in s_band.groupby("h"):
            r = _coverage(g, level)
            r["level"], r["h"] = level, int(hz)
            rows.append(r)
    cov_h = pd.DataFrame(rows)
    for level in PI.REPORT_LEVELS:
        C.log(f"  stated {level:.0%}:")
        C.log(f"    {'seasons ahead':<16}{'n':>8}{'covered':>10}{'below':>9}"
              f"{'above':>9}{'width':>9}")
        for _, r in cov_h[cov_h["level"] == level].iterrows():
            flag = "   <-- overconfident" if r["covered"] < level - 0.03 else ""
            C.log(f"    {int(r['h']):<16}{int(r['n']):>8}{r['covered']:>10.3f}"
                  f"{r['below']:>9.3f}{r['above']:>9.3f}{r['width']:>9.2f}{flag}")
        C.log("")

    # ---- 4. coverage by subgroup within horizon ---------------------------
    C.log("REPORT 4  COVERAGE BY SUBGROUP, WITHIN HORIZON. The forecast's")
    C.log("errors have already been shown to differ by tier and by age; there")
    C.log("is no reason its spread would not. A band fitted on everybody can")
    C.log("be right on average and wrong on the players who carry the money.")
    C.log("")
    sub_rows = []
    for col, label in [("tier", "trailing level"), ("pos", "position"),
                       ("exp_band", "experience"), ("age_band", "age band")]:
        if s_band[col].isna().all():
            C.log(f"  by {label}: no rows classified on this machine, skipped")
            C.log("")
            continue
        C.log(f"  by {label}, at the stated 80%:")
        C.log(f"    {'group':<16}" + "".join(f"{f'h{k}':>9}" for k in
                                             sorted(s_band['h'].unique())))
        for grp, g in s_band.groupby(col, observed=True):
            cells = []
            for hz in sorted(s_band["h"].unique()):
                gg = g[g["h"] == hz]
                c = _coverage(gg, 0.80) if len(gg) else None
                cells.append(f"{c['covered']:>9.3f}" if c is not None else f"{'-':>9}")
                if c is not None:
                    sub_rows.append({"by": label, "group": str(grp), "h": int(hz),
                                     **c.to_dict(), "level": 0.80})
            C.log(f"    {str(grp):<16}" + "".join(cells))
        C.log("")

    # ---- 5. is an under-covering group the band's fault or the forecast's? --
    C.log("REPORT 5  WHEN A GROUP IS UNDER-COVERED, WHICH HALF IS WRONG? A band")
    C.log("can miss too often for two quite different reasons, and the fix is")
    C.log("opposite in the two cases. If the forecast is centred too low for a")
    C.log("group, a correctly sized band around it misses high -- and widening")
    C.log("the band would hide a known bias behind a bigger interval instead of")
    C.log("fixing it. If the group's outcomes are genuinely more spread than the")
    C.log("pooled shape allows, the band itself is too narrow.")
    C.log("")
    C.log("EACH MISS IS DIVIDED BY THE BAND ITS OWN PAGE GAVE IT. An earlier")
    C.log("version used the last page's calibrator for every page while saying")
    C.log("it did otherwise; a 2015 forecast was handed a different scale and a")
    C.log("different shape from a 2021 one.")
    C.log("")
    C.log("This conditions on the player having played, so it says nothing about")
    C.log("the participation half of the forecast, and the coverage table above")
    C.log("includes both. It narrows where to look. It does not apportion the")
    C.log("coverage gap between a low centre and a narrow band, and the share")
    C.log("carried by each is NOT established here.")
    C.log("")
    pl = s_band[s_band["played"]].copy()
    pl["mu"] = pl["rate_82"] * pl["gp_share"]
    sg = np.full(len(pl), np.nan)
    p95 = np.full(len(pl), np.nan)
    for (pg, hz), idx in pl.groupby(["page", "h"]).groups.items():
        sp = banded.spreads_[int(pg)]
        k = pl.index.get_indexer(idx)
        sg[k] = sp.sigma(int(hz), pl.loc[idx, "mu"])
        p95[k] = float(np.quantile(sp.zs_, 0.95))
    pl["z"] = (pl["act_war"].fillna(0.0) - pl["mu"]).to_numpy() / np.maximum(sg, 1e-9)
    pl["over95"] = pl["z"].to_numpy() > p95
    shape_rows = []
    for col, label in [("tier", "trailing level"), ("age_band", "age band")]:
        if s_band[col].isna().all():
            continue
        C.log(f"  by {label}:")
        C.log(f"    {'group':<12}{'h':>3}{'n':>7}{'middle':>9}{'5th':>8}"
              f"{'95th':>8}{'5-95 span':>12}{'over own 95th':>15}")
        for grp in sorted(pl[col].dropna().unique()):
            for hz in (0, 3, 5):
                g = pl[(pl[col] == grp) & (pl["h"] == hz)]
                if len(g) < 30:
                    continue
                q = np.quantile(g["z"], [0.05, 0.5, 0.95])
                over = float(g["over95"].mean())
                C.log(f"    {str(grp):<12}{hz:>3}{len(g):>7}{q[1]:>+9.2f}"
                      f"{q[0]:>+8.2f}{q[2]:>+8.2f}{q[2] - q[0]:>12.2f}"
                      f"{over:>14.1%}")
                shape_rows.append({"by": label, "group": str(grp), "h": hz,
                                   "n": len(g), "med_z": q[1], "p05_z": q[0],
                                   "p95_z": q[2], "span": q[2] - q[0],
                                   "over_own_p95": over})
        C.log("")
    C.log("  'over own 95th' is the share of played seasons above the 95th")
    C.log("  percentile of the shape their own page was fitted with. It should")
    C.log("  be 5%. It is the sharpest single number here, because it does not")
    C.log("  depend on reading a median and a quantile together.")
    C.log("")
    pd.DataFrame(shape_rows).to_csv(
        C.out_path("uncertainty_shape_by_subgroup.csv"), index=False)

    # ---- 6. how the fitted spread compares with the realized one -----------
    C.log("REPORT 6  THE FITTED SPREAD AGAINST THE REALIZED ONE, PAGE BY PAGE.")
    C.log("The band is fitted by replaying the model on pages inside its own")
    C.log("training window, so the misses it learns from should be a little")
    C.log("smaller than the misses it goes on to make.")
    C.log("")
    C.log("WHAT THIS IS NOT. It is not an experiment that isolates overfitting.")
    C.log("Each page's fitted misses and its realized ones are different")
    C.log("mixtures of seasons and players, so the ratio carries that difference")
    C.log("as well as any optimism, and the two cannot be separated by looking")
    C.log("at them. Reported as a descriptive spread of ratios, page by page, so")
    C.log("the variation is visible rather than averaged into one number that")
    C.log("would read as an estimate. NO INFLATION IS APPLIED ON THIS EVIDENCE.")
    C.log("")
    C.log(f"    {'page':<8}{'fitted 10-90':>14}{'realized 10-90':>16}{'ratio':>9}")
    ratios = []
    for pg in sorted(pl["page"].unique()):
        g = pl[pl["page"] == pg]
        q_out = np.quantile(g["z"], [0.10, 0.90])
        q_fit = np.quantile(banded.spreads_[int(pg)].zs_, [0.10, 0.90])
        r = float((q_out[1] - q_out[0]) / (q_fit[1] - q_fit[0]))
        ratios.append(r)
        C.log(f"    {int(pg):<8}{q_fit[1] - q_fit[0]:>14.2f}"
              f"{q_out[1] - q_out[0]:>16.2f}{r:>9.3f}")
    C.log(f"    {'range':<8}{'':>14}{'':>16}{min(ratios):>6.3f}-{max(ratios):.3f}")
    C.log("")

    # ---- 6b. the distribution's mean is the forecast ----------------------
    C.log("REPORT 6b  THE DISTRIBUTION'S MEAN IS THE POINT FORECAST. The")
    C.log("wrapper's promise is that it adds a band and moves nothing. Keeping")
    C.log("the forecast COLUMNS unchanged is not enough to keep that promise: a")
    C.log("distribution whose own mean sits above the number in the column has")
    C.log("moved the forecast without moving the column, which is worse, because")
    C.log("nothing downstream would notice. The simulation averages drawn paths,")
    C.log("so its answer is this mean and not that column.")
    C.log("")
    C.log("Read by integrating the quantile function the wrapper actually")
    C.log("returns, not from the algebra, so a mistake in the inversion or in")
    C.log("the handling of the lump would show up here too.")
    C.log("")
    samp = s_band.sample(n=min(4000, len(s_band)), random_state=20260915)
    gaps = []
    for (pg, hz), g in samp.groupby(["page", "h"]):
        sp = banded.spreads_[int(pg)]
        mu = (g["rate_82"] * g["gp_share"]).to_numpy()
        got = sp.mean(int(hz), mu, g["p_play"].to_numpy())
        gaps.append(got - g["pred_war"].to_numpy())
    gaps = np.concatenate(gaps)
    C.log(f"    {len(gaps)} rows sampled: mean gap {gaps.mean():+.5f} wins, "
          f"largest {np.abs(gaps).max():.5f}")
    worst_mean = float(np.abs(gaps).max())
    assert worst_mean < 0.01, (
        f"the distribution's mean is up to {worst_mean:.4f} wins away from the "
        "forecast it is supposed to be built around")
    C.log(f"    centring removed {banded.spread_.shape_mean_raw_:+.4f} from the")
    C.log("    shape. That is the average miss the forecast makes on seasons")
    C.log("    that happened, and it is reported rather than absorbed: left in,")
    C.log("    it would have shifted every drawn path upward while the forecast")
    C.log("    column beside it read the old number.  [PASS]")
    C.log("")

    # ---- 7. the zero-spread identity --------------------------------------
    C.log("REPORT 7  THE ZERO-SPREAD IDENTITY. Set the spread to nothing and")
    C.log("make participation certain, and every quantile must land exactly on")
    C.log("the point forecast. A distribution that does not collapse to its own")
    C.log("mean when the uncertainty is removed is not a distribution around")
    C.log("that mean, and the Phase 5 simulation will inherit whatever is wrong")
    C.log("here.")
    C.log("")
    pt = (pl["rate_82"] * pl["gp_share"]).to_numpy()[:5000]
    zero = np.zeros(1001)
    worst_id = 0.0
    for q in (0.05, 0.10, 0.50, 0.90, 0.95):
        x = PI.mixture_quantile(q, np.ones_like(pt), pt, np.full_like(pt, 1e-12), zero)
        worst_id = max(worst_id, float(np.max(np.abs(x - pt))))
    assert worst_id < 1e-6, f"the zero-spread identity fails by {worst_id:.3e}"
    C.log(f"    largest gap across five quantiles and {len(pt)} rows: "
          f"{worst_id:.1e}  [PASS]")
    C.log("")

    cov_h.to_csv(C.out_path("uncertainty_coverage_by_horizon.csv"), index=False)
    pd.DataFrame(sub_rows).to_csv(
        C.out_path("uncertainty_coverage_by_subgroup.csv"), index=False)
    C.log(f"  wrote {C.out_path('uncertainty_coverage_by_horizon.csv').name} and "
          f"{C.out_path('uncertainty_coverage_by_subgroup.csv').name}")
    if not real_ages:
        C.log("")
        C.log("!! REMINDER: the ages on the scored pages were too thin for a")
        C.log("!! result. The reports above show that the machinery works, not")
        C.log("!! what the model's spread is.")
    C.write_log("uncertainty_run_log.txt")


if __name__ == "__main__":
    main()
