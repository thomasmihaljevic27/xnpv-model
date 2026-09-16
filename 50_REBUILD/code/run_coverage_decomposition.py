"""run_coverage_decomposition.py -- why does the band miss the stars?

EXPERIMENTAL (50_REBUILD). Development pages only; the confirmatory seal is
not touched. Nothing here is a candidate model.

THE QUESTION THIS ANSWERS
    The stated 80% band holds 82-84% of seasons overall and 61% for players
    with 3+ trailing wins five seasons out. Two independent reviews have now
    asked the same thing about that gap and neither the coverage table nor the
    residual diagnostic can answer it: how much of it is the forecast sitting
    too low, how much is the band being too narrow, and how much is the
    probability of playing being wrong?

    The three are not interchangeable and the repair is different for each.
    A low centre is fixed in the forecast, which is Phase 1 work and moves
    every score on record. A narrow band is fixed here, in the spread. A wrong
    participation probability is fixed in Phase 2. Guessing wrong means
    spending a phase of work on the wrong half of the model.

HOW IT ANSWERS IT: ORACLE LEVERS, WHICH ARE NOT A MODEL
    Each lever is set to the value the outcomes say it should have had, for
    that subgroup, at that horizon, and coverage is recomputed. That uses the
    answer to grade the question, deliberately. It is not a proposal and it is
    not fitted for use: it measures the CEILING each lever could reach if it
    were repaired perfectly, on this sample, with hindsight.

    Read it as an upper bound on what each repair can buy, not as a forecast
    of what a real repair would buy. A lever that cannot close the gap even
    with hindsight certainly cannot close it without.

    - THE CENTRE. Shift the forecast for the whole group until its standardised
      misses sit where the band's own shape says they should. This is the
      star residual, expressed as the amount the band would have to be
      recentred by.
    - THE SPREAD. Stretch the band for the whole group until its realized
      middle-90 span matches the shape's. This is the fat upper tail.
    - PARTICIPATION. Replace the predicted probability of playing with the
      share of the group that actually played. This is the lump on zero being
      the wrong size.

    Applied one at a time and then together. THEY DO NOT ADD UP: the interval
    is a nonlinear function of all three, so the single-lever gains will not
    sum to the all-three gain, and the gap between the sum and the joint
    figure is reported rather than hidden.

WHAT IT CANNOT SETTLE
    A lever can look powerful here because it is genuinely the defect, or
    because it is a flexible enough knob to absorb somebody else's defect.
    Shifting a centre and widening a band both raise coverage, and on a
    subgroup whose misses are skewed they can substitute for each other. The
    tell is WHICH TAIL each one fixes, so the two tails are reported
    separately throughout: a lever that repairs the side it should and leaves
    the other alone is doing its own job.
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
from player_season_table import build as build_table, birthdate_source
from ability_forecast import A1HingeExposure

SCRIPT_VERSION = "1.0"

LEADER = A1HingeExposure
LEVEL = 0.80
TAIL = (1 - LEVEL) / 2

# The groups the two reviews named, plus the one that fails in the other
# direction. 34-and-over over-covers, and a decomposition that only ever looks
# at the groups it is too narrow for would learn half the lesson.
GROUPS = [("tier", "3+"), ("age_band", "<=22"), ("tier", "1 to 2"),
          ("age_band", "34+")]
MIN_ROWS = 60


def _prepare(s: pd.DataFrame, banded) -> pd.DataFrame:
    """Attach, to every scored row, the pieces its own page's band was built
    from. Every lever below is a change to one of these three columns."""
    d = s.copy()
    d["mu"] = d["rate_82"] * d["gp_share"]
    d["sigma"] = np.nan
    for (pg, hz), idx in d.groupby(["page", "h"]).groups.items():
        sp = banded.spreads_[int(pg)]
        d.loc[idx, "sigma"] = sp.sigma(int(hz), d.loc[idx, "mu"])
    d["y"] = d["act_war"].fillna(0.0)
    return d


def _coverage(g: pd.DataFrame, zs: np.ndarray, mu, sigma, p_play) -> dict:
    lo = PI.mixture_quantile(TAIL, p_play, mu, sigma, zs)
    hi = PI.mixture_quantile(1 - TAIL, p_play, mu, sigma, zs)
    y = g["y"].to_numpy()
    return {"covered": float(((y >= lo) & (y <= hi)).mean()),
            "below": float((y < lo).mean()),
            "above": float((y > hi).mean()),
            "width": float((hi - lo).mean())}


def _levers(g: pd.DataFrame, zs: np.ndarray) -> dict:
    """The three oracle adjustments for one subgroup at one horizon."""
    mu = g["mu"].to_numpy()
    sigma = g["sigma"].to_numpy()
    p = g["p_play"].to_numpy()

    played = g["played"].to_numpy()
    out = {"n": len(g), "n_played": int(played.sum())}

    # THE CENTRE, in units of the band. Measured on the players who played,
    # because a standardised miss is only defined for a season that happened,
    # and then applied to the whole group -- a forecast that is too low is too
    # low for the man who got hurt as well as the man who did not.
    z = (g["y"].to_numpy() - mu) / np.maximum(sigma, 1e-9)
    shift = (np.median(z[played]) - np.median(zs)) if played.sum() >= 20 else 0.0
    out["shift"] = float(shift)

    # THE SPREAD, as the ratio of realized middle-90 span to the shape's.
    if played.sum() >= 20:
        span_g = float(np.diff(np.quantile(z[played], [0.05, 0.95]))[0])
        span_z = float(np.diff(np.quantile(zs, [0.05, 0.95]))[0])
        stretch = span_g / span_z
    else:
        stretch = 1.0
    out["stretch"] = float(stretch)

    # PARTICIPATION, as the share who actually played.
    out["p_pred"] = float(p.mean())
    out["p_real"] = float(played.mean())

    base = _coverage(g, zs, mu, sigma, p)
    out["base"] = base
    out["centre"] = _coverage(g, zs, mu + shift * sigma, sigma, p)
    out["spread"] = _coverage(g, zs, mu, sigma * stretch, p)
    out["play"] = _coverage(g, zs, mu, sigma, np.full_like(p, out["p_real"]))
    out["all"] = _coverage(g, zs, mu + shift * sigma, sigma * stretch,
                           np.full_like(p, out["p_real"]))
    return out


def main() -> None:
    C.banner("run_coverage_decomposition.py", SCRIPT_VERSION)
    path, how = birthdate_source()
    table = build_table(birthdate_csv=path, verbose=False)
    dev = table[table["syr"] >= min(C.DEV_PAGES)]
    C.log(f"  birthdates: {how}")
    C.log(f"  age coverage {float(dev['has_age'].mean()):.1%} on "
          f"{min(C.DEV_PAGES)} and later")
    if float(dev["has_age"].mean()) < C.MIN_AGE_COVERAGE:
        C.log("!! ages too thin on the scored pages; the figures below are not evidence")
    C.log("")

    h = H.Harness(table)
    banded = PI.WithIntervals(LEADER())
    s = _prepare(h.run(banded), banded)

    C.log("EVERY LEVER IS SET WITH HINDSIGHT. Each is given the value this")
    C.log("subgroup's own outcomes say it should have had, so what is measured")
    C.log("is the CEILING a perfect repair could reach on this sample. None of")
    C.log("it is a candidate model and none of it is fitted for use.")
    C.log("")

    rows = []
    for col, grp in GROUPS:
        C.log(f"=== {grp} ({col.replace('_', ' ')}) "
              + "=" * max(0, 50 - len(grp) - len(col)))
        C.log(f"  {'h':>2}{'n':>6}{'played':>8}{'base':>8}{'centre':>8}"
              f"{'spread':>8}{'play':>7}{'all':>8}   {'shift':>7}{'stretch':>8}"
              f"{'p pred':>8}{'p real':>8}")
        for hz in sorted(s["h"].unique()):
            g = s[(s[col] == grp) & (s["h"] == hz)]
            if len(g) < MIN_ROWS:
                continue
            # One page's shape stands for the group at this horizon. The seven
            # development pages' shapes differ by less than a hundredth at
            # every reported quantile, so this is a reporting convenience and
            # not a modelling choice; the per-page scales are already in
            # `sigma` row by row.
            zs = banded.spreads_[max(banded.spreads_)].zs_
            r = _levers(g, zs)
            C.log(f"  {int(hz):>2}{r['n']:>6}{r['n_played']:>8}"
                  f"{r['base']['covered']:>8.3f}{r['centre']['covered']:>8.3f}"
                  f"{r['spread']['covered']:>8.3f}{r['play']['covered']:>7.3f}"
                  f"{r['all']['covered']:>8.3f}   {r['shift']:>+7.2f}"
                  f"{r['stretch']:>8.2f}{r['p_pred']:>8.3f}{r['p_real']:>8.3f}")
            flat = {"group": grp, "by": col, "h": int(hz), "n": r["n"],
                    "n_played": r["n_played"], "shift": r["shift"],
                    "stretch": r["stretch"], "p_pred": r["p_pred"],
                    "p_real": r["p_real"]}
            for k in ("base", "centre", "spread", "play", "all"):
                for kk, vv in r[k].items():
                    flat[f"{k}_{kk}"] = vv
            rows.append(flat)
        C.log("")

    d = pd.DataFrame(rows)
    d.to_csv(C.out_path("coverage_decomposition.csv"), index=False)

    # ---- which lever, and does it fix the side it should? -----------------
    C.log("WHICH LEVER, AND DOES IT REPAIR THE RIGHT SIDE? A lever that raises")
    C.log("coverage by fixing the tail that was actually too thin is doing its")
    C.log("own job. One that raises coverage by fattening the other side is")
    C.log("absorbing somebody else's defect and would not survive being asked")
    C.log("to do it without hindsight.")
    C.log("")
    C.log("Gap closed, as a share of the distance from base coverage to the")
    C.log("stated 80%, at the horizons where the base is short of it:")
    C.log("")
    C.log(f"  {'group':<10}{'h':>3}{'base':>8}{'centre':>9}{'spread':>9}"
          f"{'play':>8}{'all':>8}{'sum-all':>9}")
    for _, r in d.iterrows():
        if r["base_covered"] >= LEVEL - 0.005:
            continue
        gap = LEVEL - r["base_covered"]
        parts = {k: (r[f"{k}_covered"] - r["base_covered"]) / gap
                 for k in ("centre", "spread", "play", "all")}
        C.log(f"  {r['group']:<10}{int(r['h']):>3}{r['base_covered']:>8.3f}"
              f"{parts['centre']:>9.0%}{parts['spread']:>9.0%}"
              f"{parts['play']:>8.0%}{parts['all']:>8.0%}"
              f"{parts['centre'] + parts['spread'] + parts['play'] - parts['all']:>+9.0%}")
    C.log("")
    C.log("  'sum-all' is how much the three single-lever gains overshoot the")
    C.log("  joint one. It is not an error: the interval is a nonlinear")
    C.log("  function of the three, so they overlap, and a large overshoot")
    C.log("  means two levers are repairing the same miss.")
    C.log("")

    C.log("THE TAILS, at the horizons where the base coverage is short. 'below'")
    C.log("is the share of seasons under the band's lower end and 'above' the")
    C.log("share over its upper end; at a stated 80% each should be 10%.")
    C.log("")
    C.log(f"  {'group':<10}{'h':>3}{'':>4}{'base':>14}{'centre':>14}"
          f"{'spread':>14}{'play':>14}")
    for _, r in d.iterrows():
        if r["base_covered"] >= LEVEL - 0.005:
            continue
        cells = "".join(f"{r[f'{k}_below']:>6.2f}/{r[f'{k}_above']:<7.2f}"
                        for k in ("base", "centre", "spread", "play"))
        C.log(f"  {r['group']:<10}{int(r['h']):>3}{'':>4}{cells}")
    C.log("")

    # ---- participation, measured directly ---------------------------------
    C.log("PARTICIPATION, WITHOUT THE ORACLE. The lever above is a subgroup")
    C.log("average swapped for the truth, which says how much coverage it could")
    C.log("buy but not what is wrong with it. This is the thing itself: the")
    C.log("probability the model gave, against the share who actually played.")
    C.log("No hindsight is used to set anything here; the two columns are just")
    C.log("put side by side.")
    C.log("")
    for col, label in [("tier", "trailing level"), ("age_band", "age band")]:
        C.log(f"  by {label}  (predicted / actual):")
        C.log(f"    {'group':<10}" + "".join(f"{'h' + str(k):>14}"
                                             for k in sorted(s['h'].unique())))
        for grp in sorted(s[col].dropna().unique()):
            cells = []
            for hz in sorted(s["h"].unique()):
                g = s[(s[col] == grp) & (s["h"] == hz)]
                if len(g) < MIN_ROWS:
                    cells.append(f"{'-':>14}")
                    continue
                cells.append(f"{g['p_play'].mean():>6.3f}/"
                             f"{g['played'].mean():<7.3f}")
            C.log(f"    {str(grp):<10}" + "".join(cells))
        C.log("")
    C.log("  and in aggregate, where the subgroup errors partly cancel:")
    C.log(f"    {'h':<4}{'predicted':>11}{'actual':>9}{'brier':>9}")
    for hz in sorted(s["h"].unique()):
        g = s[s["h"] == hz]
        C.log(f"    {int(hz):<4}{g['p_play'].mean():>11.3f}"
              f"{g['played'].mean():>9.3f}{g['brier'].mean():>9.4f}")
    C.log("")

    # ---- and the point bias, split the same three ways --------------------
    C.log("THE POINT BIAS, SPLIT THE SAME THREE WAYS, ALSO WITHOUT HINDSIGHT.")
    C.log("Coverage is about the band; this is about the number in the middle of")
    C.log("it. The season total is the probability of playing times the rate")
    C.log("times the share of the schedule, so a bias in the total has three")
    C.log("places it can come from, and they are measured separately here. The")
    C.log("rate and games columns are conditional on the player having played,")
    C.log("which is the event those two halves of the forecast are about.")
    C.log("")
    C.log("A group whose total is badly biased while its rate is not has a")
    C.log("participation problem wearing a forecasting problem's clothes.")
    C.log("")
    for col, label in [("tier", "trailing level"), ("age_band", "age band")]:
        C.log(f"  by {label}:")
        C.log(f"    {'group':<10}{'h':>3}{'n':>7}{'total bias':>12}"
              f"{'rate bias':>11}{'games-share bias':>18}{'p_play error':>14}")
        for grp in sorted(s[col].dropna().unique()):
            for hz in (0, 3, 5):
                g = s[(s[col] == grp) & (s["h"] == hz)]
                if len(g) < MIN_ROWS:
                    continue
                pl = g[g["played"]]
                C.log(f"    {str(grp):<10}{int(hz):>3}{len(g):>7}"
                      f"{g['e_war'].mean():>+12.3f}"
                      f"{(pl['rate_82'] - pl['act_rate_82']).mean():>+11.3f}"
                      f"{(pl['gp_share'] - pl['act_gp_share']).mean():>+18.3f}"
                      f"{g['p_play'].mean() - g['played'].mean():>+14.3f}")
        C.log("")

    C.log(f"  wrote {C.out_path('coverage_decomposition.csv').name}")
    C.write_log("coverage_decomposition_run_log.txt")


if __name__ == "__main__":
    main()
