"""run_star_walk_diagnostic.py -- where the aging walk and the stars part
company. A HINDSIGHT DIAGNOSTIC, not a forecast and not a candidate.

EXPERIMENTAL (50_REBUILD). Development pages 2015-2021 only. Nothing is fitted
that a forecast could use, and nothing is adopted.

THE QUESTION
    On the adopted skater leader the three-win-and-up tier's rate is right at
    the valuation season and then walked down about 0.27 per 82 a season,
    where the stars who played lost about 0.09. The aging curve, on its own
    training pairs, matches one-season changes grouped by the previous
    season's rate. This run localises the difference; it is not a two-way
    test. A good first step would not show that repeating the step causes the
    later miss, and a bad one would not show that group membership does.

THE GROUP
    The harness's own reporting tier, `forecast_harness.subjects_at` with
    tier == "3+": a 60/40 total over the two latest qualifying seasons, falling
    back to the latest, then the second, then the third. Membership is fixed
    per player and page across every arm.

THE FIT
    For each page the adopted leader is fitted ONCE on what the page could see
    and FROZEN. Its aging curve (survivorship-imputed, one-season lagged level)
    and its projected path are read from that fit. The first aging transition
    is the page season to the next; the season before the page is not a step
    of the walk.

THE ROWS
    A transition is season t to t+1 for t = page .. page+4, kept only where
    the player played t-1, t and t+1 (each at least the qualifying games),
    so every arm is compared on the SAME rows with the SAME weights: the
    smaller of the two seasons' games, as the curve is fitted. Counts at each
    stage are reported, because rate changes cannot be observed for players
    who do not play both seasons.

THE ARMS, all through the same frozen curve (`AdditiveAging.step`)
    1. training-aligned: age at t and the actual rate at t-1 -- how the curve
       was fitted (HINDSIGHT: t-1 after the page is a realised season);
    2. current-level: the same age and rows, the actual rate at t -- the
       timing the walk uses, on realised levels (HINDSIGHT);
    3. forecast path: the page's own projected levels, step k = level(k+1) -
       level(k) with the walk's age; reported with the projected level's error
       at t, so a wrong starting level is not charged to the steps.
    Reference, not an arm: arm 1 on a survivors-only curve fitted on the same
    page, to show how much of arm 1's steepness is the imputation of departed
    players' seasons (which observed changes cannot contain by construction).

COMPARISON GROUPS, arm 1 only, same pages, dates and weights:
    the harness's "2 to 3" tier; and the curve's own kind of group, every
    subject on the page whose actual rate at t-1 was 3 or more.

AND THE FULL COHORT: season WAR by horizon for the tier from the adopted
leader's harness rows (`star_residual_v12.csv`, adopted), absences counted.
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
from aging_additive import AdditiveAging
from player_season_table import build as build_table, birthdate_source
from run_npv_simulation import LEADER

SCRIPT_VERSION = "1.0"
STEPS = range(5)                       # transitions page+k -> page+k+1


def transitions(table, page, keys, fit, proj, curve_ref):
    """Rows (player, k) with t-1, t, t+1 all played, and every arm's step."""
    s = table[table["GP"] >= C.MIN_GP].set_index(["career_key", "syr"])
    rows = []
    for ck in keys:
        for k in STEPS:
            t = page + k
            if t + 1 > C.LAST_SOURCE_SEASON:
                continue
            try:
                a, b, c = s.loc[(ck, t - 1)], s.loc[(ck, t)], s.loc[(ck, t + 1)]
            except KeyError:
                continue
            if not np.isfinite(b["age"]):
                continue
            is_d = float(b["pos"] == "D")
            r_prev, r_now, r_next = float(a["WAR_82"]), float(b["WAR_82"]), float(c["WAR_82"])
            row = {"career_key": ck, "page": page, "k": k,
                   "w": float(min(b["GP"], c["GP"])),
                   "obs": r_next - r_now, "r_now": r_now,
                   "arm1": float(fit.step([b["age"]], [r_prev], [is_d])[0]),
                   "arm2": float(fit.step([b["age"]], [r_now], [is_d])[0]),
                   "ref_surv": float(curve_ref.step([b["age"]], [r_prev], [is_d])[0])}
            if proj is not None and ck in proj.index:
                p = proj.loc[ck]
                if k in p.index and (k + 1) in p.index:
                    row["arm3"] = float(p[k + 1] - p[k])
                    row["lvl_err"] = float(p[k] - r_now)
            rows.append(row)
    return pd.DataFrame(rows)


def wmean(d, col):
    ok = d[col].notna()
    return float(np.average(d.loc[ok, col], weights=d.loc[ok, "w"])) if ok.any() else np.nan


def main() -> None:
    C.banner("run_star_walk_diagnostic.py", SCRIPT_VERSION)
    path, how = birthdate_source()
    C.log(f"  birthdates: {how}")
    table = build_table(birthdate_csv=path, verbose=False)
    C.log("  HINDSIGHT DIAGNOSTIC: arms 1 and 2 read realised seasons after the page.")
    C.log("")
    stars, twothree, curve_grp, counts = [], [], [], []
    for page in C.DEV_PAGES:
        iset = ISET.build(table, ISET.decision_date_for_page(page), t0=page)
        m = LEADER()
        m.fit(iset.seasons, before=page)              # fitted once, frozen
        ref = AdditiveAging(level_mode="lagged", selection="none").fit(iset.seasons, page)
        subs = H.subjects_at(iset)
        star = subs[subs["tier"] == "3+"]
        pr = m.predict_beyond_fit(iset, star, list(range(6)))
        proj = pr.pivot_table(index="career_key", columns="h", values="rate_82")
        d = transitions(table, page, star["career_key"], m.aging_, proj, ref)
        stars.append(d)
        tt = subs[subs["tier"] == "2 to 3"]
        twothree.append(transitions(table, page, tt["career_key"], m.aging_, None, ref))
        allp = transitions(table, page, subs["career_key"], m.aging_, None, ref)
        # the curve's own kind of group: realised rate at t-1 of 3 or more
        s = table[table["GP"] >= C.MIN_GP].set_index(["career_key", "syr"])["WAR_82"]
        lag = [s.get((ck, page + k - 1), np.nan) for ck, k in zip(allp["career_key"], allp["k"])]
        curve_grp.append(allp[np.asarray(lag, float) >= 3.0])
        counts.append({"page": page, "members": len(star), "rows": len(d)})
        C.log(f"  page {page}: {len(star)} tier members, {len(d)} transition rows")
    st = pd.concat(stars, ignore_index=True)
    tw = pd.concat(twothree, ignore_index=True)
    cg = pd.concat(curve_grp, ignore_index=True)
    C.log("")

    C.log("THE TIER'S TRANSITIONS, weighted by the smaller season's games. Change in")
    C.log("rate per 82 from t to t+1; every column on the same rows.")
    C.log("")
    C.log(f"    {'k':<3}{'rows':>6}{'observed':>10}{'arm 1':>9}{'arm 2':>9}{'arm 3':>9}"
          f"{'level err':>11}{'survivor ref':>14}")
    for k in STEPS:
        g = st[st["k"] == k]
        if g.empty:
            continue
        C.log(f"    {k:<3}{len(g):>6}{wmean(g, 'obs'):>+10.3f}{wmean(g, 'arm1'):>+9.3f}"
              f"{wmean(g, 'arm2'):>+9.3f}{wmean(g, 'arm3'):>+9.3f}{wmean(g, 'lvl_err'):>+11.3f}"
              f"{wmean(g, 'ref_surv'):>+14.3f}")
    C.log(f"    {'all':<3}{len(st):>6}{wmean(st, 'obs'):>+10.3f}{wmean(st, 'arm1'):>+9.3f}"
          f"{wmean(st, 'arm2'):>+9.3f}{wmean(st, 'arm3'):>+9.3f}{wmean(st, 'lvl_err'):>+11.3f}"
          f"{wmean(st, 'ref_surv'):>+14.3f}")
    C.log("")
    C.log("  arm 1: the frozen curve on age at t and the realised rate at t-1 (its")
    C.log("  training definition). arm 2: the same, realised rate at t (the walk's")
    C.log("  timing). arm 3: the page's projected path. level err: projected level at")
    C.log("  t minus realised rate at t. survivor ref: arm 1 on a survivors-only curve.")
    C.log("")

    C.log("COMPARISON GROUPS, arm 1 only, same pages, dates and weights:")
    for name, g in (("the tier", st), ("harness tier 2 to 3", tw),
                    ("realised rate at t-1 of 3 or more", cg)):
        C.log(f"    {name:<38}{len(g):>6} rows   observed {wmean(g, 'obs'):+.3f}   "
              f"arm 1 {wmean(g, 'arm1'):+.3f}   survivor ref {wmean(g, 'ref_surv'):+.3f}")
    C.log("")

    f = C.out_path("star_residual_v12.csv")
    if f.exists():
        h = pd.read_csv(f, low_memory=False)
        h = h[(h["variant"] == "adopted") & (h["tier"] == "3+")]
        C.log("THE FULL COHORT, season WAR, from the adopted leader's harness rows")
        C.log("(star_residual_v12.csv); absences counted, not dropped:")
        C.log(f"    {'h':<3}{'forecasts':>10}{'P(plays)':>10}{'played':>8}{'WAR bias':>10}"
              f"{'bias if played':>16}")
        for hh, g in h.groupby("h"):
            pl = g["played"] == 1
            C.log(f"    {int(hh):<3}{len(g):>10}{g['p_play'].mean():>10.3f}{pl.mean():>8.3f}"
                  f"{g['e_war'].mean():>+10.3f}{g.loc[pl, 'e_war'].mean():>+16.3f}")
        C.log("")
    st.to_csv(C.out_path("star_walk_diagnostic.csv"), index=False)
    C.write_log("star_walk_diagnostic_run_log.txt")


if __name__ == "__main__":
    main()
