"""
=============================================================================
 exit_hazard.py   v1.2                              Phase 1a (D18)
                                                     (D20, 2026-07-05)
                                          review item 1.4 (2026-07-26)
=============================================================================
 WHAT CHANGED IN v1.2 (review item 1.4 -- two cells asserted certainty)
 ----------------------------------------------------------------------
 The quality-by-age lookup was twenty raw cell means over 5,346 skater
 transitions and 502 goalie transitions. Two skater cells contained no
 observed departures at all: star aged 22 and under (0 of 26) and star
 aged 31-34 (0 of 40). A hazard of exactly zero is not a small number, it
 is a claim of certainty, so the model treated a 32-year-old star as
 certain to appear in every remaining season of an eight-year contract.
 That is the tier holding the most trade value in the league. The table
 was also non-monotone across the boundary the zero created (star 27-30 =
 1.2% against star 31-34 = 0.0%), and the whole star row rested on four
 departures in 308 player-seasons. The goalie table had three such cells
 and cannot support a saturated 20-cell fit at all.

 v1.2 replaces the cell means with a logistic model of exit on quality
 bucket and age group, main effects only -- eight parameters where there
 were twenty cell means, fitted on the same transitions. See
 build_hazard_table() for why the model rather than a pseudo-count, and
 report_item_14() for the tests that license main effects only.

 IDENTIFICATION NOTE. This tightens rather than loosens: fewer free
 parameters, same estimation window, same presence-based exit definition,
 same k-1 read in contract_npv v1.2. Exit is a row-presence flag in the
 WAR file, so nothing about it is downstream of a valuation -- no new
 circularity. The one exposure it does not touch is that the table is
 estimated over 2018-2024 and then applied to decisions inside that
 window, which is logged separately as review item 5.1.

 DEPENDENCY NOTE. This file now imports statsmodels (the fit) and scipy
 (the likelihood-ratio test in the report). Both are already used
 elsewhere in the project, but v1.1 ran on numpy and pandas alone, so a
 bare environment that used to run this file will now need them.
=============================================================================
 WHAT THIS ESTIMATES (plain English)
 -----------------------------------
 The model's projections assume the player keeps playing. Sometimes he
 simply doesn't -- career-ending injury, leaving for Europe, retirement.
 This script measures how often that actually happens: for every skater
 who played a real NHL season, what is the chance he has NO NHL season at
 all the following year? That yearly "exit hazard" (h) is the missing risk
 piece of the discount structure (D16): each future season's projected
 value gets multiplied by the probability the player is still around to
 produce it, while the cap-growth rate (g = 3%, D17, shared with D11)
 sits in the denominator.

 WHY THIS DOESN'T DOUBLE-COUNT THE AGING CURVE (the D18 care-point)
 ------------------------------------------------------------------
 The aging curve is built from within-player year-over-year changes --
 which mechanically require the player to appear in BOTH seasons. It is
 therefore estimated entirely on survivors and knows nothing about exits.
 Likewise D12 v3 (replacement reversion) handles players who collapse but
 KEEP PLAYING. The exit hazard covers exactly the one margin neither of
 those touches: the player vanishing from the league entirely. Clean
 separation, no overlap.

 DESIGN CHOICES (all flagged)
 ----------------------------
 * Population: player-seasons with GP >= 10 -- the same qualifying filter
   the valuation anchor uses, so the hazard describes the population the
   model actually prices. (GP >= 1 reported as a sensitivity.)
 * Transition years t = 2018..2024 (exit observed at t+1, so the last
   usable t is 2024). Matches the back-test window AND the range where
   the age join is essentially complete -- estimating on older years
   would UNDERCOUNT exits, because the players the age join misses are
   precisely the pre-2018 retirees.
 * Exit = no WAR.csv row of any GP at t+1. "Returned later" (present at
   t+2 or t+3 after missing t+1) is reported as a diagnostic so a
   Europe-year-then-comeback isn't silently treated as a career end.
 * Quality buckets use the SEASON's raw WAR (negative / 0-1 / 1-3 / 3+),
   mirroring the D14(c) buckets, so the hazard can later be applied to
   projected WAR season by season.
 * COVID caveat: transitions into 2020-21 (taxi squads, opt-outs, Europe
   loans) may inflate exits; the year-by-year table below makes any such
   spike visible before we lock a pooled number.
=============================================================================
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd

from dotenv import load_dotenv

load_dotenv()

SOURCE_DIR = Path(os.environ["SOURCE_DIR"])   # vendor inputs, read-only
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])   # generated files land here
F_WAR = SOURCE_DIR / "WAR.csv"
F_WAR_AGE = OUTPUT_DIR / "WAR_with_age.csv"   # generated by age_join.py
OUT_LOG = OUTPUT_DIR / "exit_hazard_run_log.txt"

T_FIRST, T_LAST = 2018, 2024          # transition years (exit read at t+1)
MIN_GP = 10                           # anchor-qualifying population

LOG = []
def log(msg=""):
    print(msg)
    LOG.append(str(msg))


def bucket(war):
    if war < 0: return "negative"
    if war < 1: return "fringe"
    if war < 3: return "regular"
    return "star"


def age_group(a):
    if pd.isna(a): return "unknown"
    if a <= 22: return "<=22"
    if a <= 26: return "23-26"
    if a <= 30: return "27-30"
    if a <= 34: return "31-34"
    return "35+"


def build_transitions(war_path, age_path, name_col="Player",
                      min_gp=MIN_GP, t_first=T_FIRST, t_last=T_LAST):
    """The shared construction: one row per qualifying player-season with
    an exited/returned flag. Used by this script's report AND imported by
    contract_npv.py, so the NPV engine can never drift from the documented
    estimation. Works for the goalie panel too (name_col="Goalie",
    age_path=None -- goalie ages ride in from the contract spine later)."""
    war = pd.read_csv(war_path)
    war["syr"] = war["Season"].str.split("-").str[0].astype(int) + 2000
    # team-split seasons collapse to one row per player-season, WAR summed
    war = (war.groupby([name_col, "syr"], as_index=False)
              .agg(WAR=("WAR", "sum"), GP=("GP", "sum")))
    # D20 (2026-07-05): schedule proration before QUALITY bucketing, so a
    # 3.5-WAR-pace player in the 56-game season buckets as the star he
    # was, not the "regular" his raw total says. Exit detection below is
    # presence-based and untouched by scaling.
    try:
        from skater_value_engine import PRORATION as _PR
    except ImportError:
        _PR = {2019: 82 / 70, 2020: 82 / 56}
    war["WAR"] = war["WAR"] * war["syr"].map(_PR).fillna(1.0)
    present = set(zip(war[name_col], war["syr"]))
    age_map = {}
    if age_path is not None:
        wa = pd.read_csv(age_path)
        wa["syr"] = wa["Season"].str.split("-").str[0].astype(int) + 2000
        age_map = wa.set_index([name_col, "syr"])["age"].to_dict()
    rows = []
    q = war[(war["GP"] >= min_gp) & war["syr"].between(t_first, t_last)]
    for r in q.itertuples():
        nm = getattr(r, name_col)
        exited = (nm, r.syr + 1) not in present
        returned = exited and (((nm, r.syr + 2) in present)
                               or ((nm, r.syr + 3) in present))
        rows.append({"player": nm, "t": r.syr, "war": r.WAR,
                     "gp": r.GP, "age": age_map.get((nm, r.syr)),
                     "bucket": bucket(r.WAR),
                     "age_grp": age_group(age_map.get((nm, r.syr))),
                     "exited": exited, "returned_later": returned})
    return pd.DataFrame(rows)


BUCKETS = ["star", "regular", "fringe", "negative"]
AGE_GROUPS = ["<=22", "23-26", "27-30", "31-34", "35+"]


def _fit_additive(d):
    """Fit the smooth risk model: exit on quality bucket + age group, main
    effects only, logistic. Eight parameters where the raw table had twenty
    cell means.

    Why main effects only. A full interaction model IS the raw table, cell
    for cell, so the question is whether the cells carry information beyond
    quality and age acting separately. They do not: the additive-against-
    interaction likelihood-ratio test returns p=0.955 for skaters and
    p=0.956 for goalies, and the goalie interaction model does not even
    converge on 502 transitions. Reported in main()."""
    import statsmodels.formula.api as smf          # see header dependency note
    dd = d[d["age_grp"] != "unknown"].copy()
    dd["y"] = dd["exited"].astype(int)
    res = smf.logit('y ~ C(bucket) + C(age_grp)', data=dd).fit(disp=0)
    if not res.mle_retvals.get("converged", False):
        # Newton can stall on rare-event data; BFGS is the documented retry.
        res = smf.logit('y ~ C(bucket) + C(age_grp)', data=dd).fit(
            disp=0, method="bfgs", maxiter=500)
    assert res.mle_retvals.get("converged", False), \
        "hazard model failed to converge under both Newton and BFGS -- do " \
        "not price anything off this table"
    return res, dd


def build_hazard_table(d):
    """Quality-x-age hazard lookup from a transition table, plus per-bucket
    marginals (key (bucket, "ALL")) as the fallback when age is unknown.

    REVIEW ITEM 1.4. Cells come from the fitted additive model, not from raw
    cell means. The raw table asserted CERTAINTY in two places -- star aged
    22 and under read 0.0% on 26 observations, star aged 31-34 read 0.0% on
    40 -- so the model treated a 32-year-old star as certain to play every
    remaining season of an eight-year contract. It was also non-monotone
    (star 27-30 = 1.2% against star 31-34 = 0.0%), and the entire star row
    rested on four exits in 308 player-seasons.

    Why the model rather than a pseudo-count. A fixed pseudo-count of 10 --
    the device aging_curve.py uses -- moves star 31-34 from 0.00% to 0.24%,
    which is still 98% survival across eight years and still lower than the
    younger cell, because 40 observations outweigh a pseudo-count of 10 four
    to one. Fitting the shrinkage weight instead of choosing it (beta-
    binomial, prior mean at the model prediction) sends it to the upper
    bound, i.e. the data show no cell-level deviation from the additive
    model worth preserving. Cost of the switch, where real data exists: the
    worst deviation across the twelve cells with n>=150 is 2.21 percentage
    points (fringe 31-34, raw 15.8% against model 13.6%).

    Deliberately NOT done: no monotonicity is imposed. The fitted table dips
    slightly from 23-26 to 27-30 in every bucket, and that dip is in the raw
    data too -- young marginal players churn. Smoothing it would be a prior,
    not a finding.

    The (bucket, "ALL") fallback stays a RAW marginal. It conditions on no
    age, so there is no age gradient to borrow. Cells keyed on the literal
    age group "unknown" are no longer emitted at all: they held one or two
    observations each and were being returned to any player with a missing
    birthdate ahead of the marginal. Those lookups now fall through to
    (bucket, "ALL") as intended -- 2 skater rows and 1 goalie row.
    """
    res, dd = _fit_additive(d)
    obs_b = set(dd["bucket"]); obs_g = set(dd["age_grp"])
    grid = pd.DataFrame([(b, g) for b in BUCKETS for g in AGE_GROUPS
                         if b in obs_b and g in obs_g],
                        columns=["bucket", "age_grp"])
    grid["p"] = res.predict(grid)

    tab = {(r.bucket, r.age_grp): float(r.p) for r in grid.itertuples()}
    for b, grp in d.groupby("bucket"):
        tab[(b, "ALL")] = float(grp["exited"].mean())   # raw, by design

    # ---- guards ------------------------------------------------------------
    # (1) The defect this item exists to remove: no cell may assert certainty
    #     in either direction.
    cells = {k: v for k, v in tab.items() if k[1] != "ALL"}
    assert cells, "hazard table produced no age-conditioned cells"
    assert all(0.0 < v < 1.0 for v in cells.values()), \
        "a hazard cell is exactly 0 or 1 -- the model asserts certainty"
    assert all(np.isfinite(v) for v in tab.values()), "non-finite hazard cell"
    # (2) No "unknown" age cell may survive: those lookups must fall through
    #     to the raw bucket marginal.
    assert not any(k[1] == "unknown" for k in tab), \
        "an unknown-age cell was emitted -- it would shadow the marginal"
    # (3) Calibration. Weighting the fitted cells by their observed counts
    #     must reproduce the observed overall exit rate. This is the check
    #     that catches a mis-specified or mis-joined fit: the model may
    #     redistribute risk across cells but it cannot invent or destroy it.
    n = dd.groupby(["bucket", "age_grp"]).size()
    implied = sum(n.get(k, 0) * v for k, v in cells.items()) / n.sum()
    observed = float(dd["exited"].mean())
    assert abs(implied - observed) < 0.005, \
        f"fitted table implies {implied:.4f} overall exit rate against " \
        f"{observed:.4f} observed -- the fit does not reproduce the panel"
    return tab


def report_item_14(d, label="SKATERS"):
    """REVIEW ITEM 1.4 audit trail. Prints the raw cell means beside the
    fitted cells, the additive-against-interaction test that justifies the
    switch, and the worst deviation on well-populated cells. Read-only; returns the report lines for the caller to log.

    Written as a standalone function so contract_npv.py or any other
    consumer can call it on its own transition panel (the goalie panel, for
    instance) without duplicating the arithmetic."""
    from scipy import stats
    import statsmodels.formula.api as smf

    L = []                      # returned rather than logged, so each caller
    def _p(m=""):               # writes into ITS OWN run log
        L.append(str(m))

    res, dd = _fit_additive(d)
    tab = build_hazard_table(d)
    n = dd.groupby(["bucket", "age_grp"]).size()
    raw = dd.groupby(["bucket", "age_grp"])["exited"].mean()
    ex = dd.groupby(["bucket", "age_grp"])["exited"].sum()

    _p(f"\n{'=' * 74}")
    _p(f"ITEM 1.4 -- {label}: thin cells replaced by the fitted risk model")
    _p("=" * 74)
    _p(f"transitions: {len(dd):,}   age unknown (falls through to the "
        f"bucket marginal): {int((d['age_grp'] == 'unknown').sum())}")

    # the test that licenses main effects only
    try:
        import warnings
        with warnings.catch_warnings():
            # The saturated fit is expected to be degenerate wherever a cell
            # holds no departures -- that separation is the very thing this
            # item exists to fix, so the warning is noise here, not news.
            warnings.simplefilter("ignore")
            full = smf.logit('y ~ C(bucket)*C(age_grp)', data=dd).fit(disp=0)
        lr = 2 * (full.llf - res.llf)
        df = int(full.df_model - res.df_model)
        p = float(stats.chi2.sf(lr, df))
        assert np.isfinite(lr) and lr >= -1e-6, "degenerate LR statistic"
        _p(f"additive vs full-interaction LR test: chi2={lr:.2f}, df={df}, "
            f"p={p:.3f}")
        _p("  A high p means the cells carry nothing beyond quality and age")
        _p("  acting separately, so main effects are not discarding structure.")
    except Exception as e:                       # goalie panel: separation
        _p(f"full-interaction model did not fit ({type(e).__name__}) -- with "
            f"{len(dd):,} transitions across 20 cells the saturated table is "
            f"not estimable, which is itself the argument for the model.")

    _p("\nraw cell mean (exits/n)  ->  fitted:")
    _p("  " + "bucket".ljust(9) + "".join(g.rjust(21) for g in AGE_GROUPS))
    for b in BUCKETS:
        line = "  " + b.ljust(9)
        for g in AGE_GROUPS:
            if (b, g) not in tab:
                line += "                  --  "
                continue
            nn, rr = int(n.get((b, g), 0)), raw.get((b, g), np.nan)
            line += (f"{rr*100:5.2f}({int(ex.get((b, g), 0))}/{nn})"
                     f"->{tab[(b, g)]*100:5.2f}").rjust(21)
        _p(line)
    _p("  bucket marginals (unknown-age fallback, raw by design): "
        + "  ".join(f"{b} {tab[(b, 'ALL')]*100:.2f}%"
                    for b in BUCKETS if (b, "ALL") in tab))

    # what the switch costs where the data is real
    dev = [(abs(tab[(b, g)] - raw[(b, g)]) * 100, b, g, int(n[(b, g)]))
           for b in BUCKETS for g in AGE_GROUPS
           if (b, g) in tab and n.get((b, g), 0) >= 150]
    if dev:
        w = max(dev)
        _p(f"\nfit on well-populated cells (n>=150, {len(dev)} cells): worst "
            f"deviation {w[0]:.2f}pp ({w[1]} {w[2]}, n={w[3]})")
    else:
        _p(f"\nno cell reaches n=150 (largest is n={int(n.max())}), so there is "
            f"no well-populated cell to check the fit against -- which is the "
            f"argument for the model rather than a caveat to it.")
    zeros = [(b, g) for b in BUCKETS for g in AGE_GROUPS
             if (b, g) in tab and n.get((b, g), 0) > 0 and raw.get((b, g)) == 0]
    _p(f"cells that read exactly 0.0% before this change: {len(zeros)} "
        + (f"-- {', '.join(f'{b} {g}' for b, g in zeros)}" if zeros else ""))
    _p("  each now carries the model's rate; none reads zero.")
    return L


def main():
    d = build_transitions(F_WAR, F_WAR_AGE)

    log("=" * 74)
    log(f"EXIT HAZARD ESTIMATION  (GP>={MIN_GP} skater-seasons, t={T_FIRST}-{T_LAST})")
    log("=" * 74)
    log(f"\nplayer-season transitions: {len(d):,}   "
        f"age coverage: {(d['age_grp'] != 'unknown').mean()*100:.1f}%")
    log(f"overall exit hazard: {d['exited'].mean()*100:.2f}% per year")
    log(f"of exiters, later returned (t+2 or t+3): "
        f"{d.loc[d['exited'], 'returned_later'].mean()*100:.1f}% "
        f"(true exits are ~{d['exited'].mean()*(1-d.loc[d['exited'],'returned_later'].mean())*100:.2f}%/yr)")

    # ---- year-by-year: is COVID distorting the pool? ------------------------
    log("\nby transition year (watch 2019->20 and 2020->21 for COVID effects):")
    yr = d.groupby("t")["exited"].agg(["mean", "count"])
    for t, r in yr.iterrows():
        log(f"    {t}->{t+1}: {r['mean']*100:5.2f}%   (n={int(r['count']):,})")

    # ---- the table that matters: hazard by quality x age --------------------
    log("\nexit hazard by QUALITY bucket (season WAR):")
    for b in ["star", "regular", "fringe", "negative"]:
        s = d[d["bucket"] == b]
        log(f"    {b:9s} {s['exited'].mean()*100:5.2f}%   (n={len(s):,})")

    log("\nexit hazard by AGE group:")
    for g in ["<=22", "23-26", "27-30", "31-34", "35+"]:
        s = d[d["age_grp"] == g]
        if len(s):
            log(f"    {g:6s} {s['exited'].mean()*100:5.2f}%   (n={len(s):,})")

    log("\nexit hazard, QUALITY x AGE (the candidate lookup table):")
    piv = d.pivot_table(index="bucket", columns="age_grp",
                        values="exited", aggfunc="mean")
    cnt = d.pivot_table(index="bucket", columns="age_grp",
                        values="exited", aggfunc="count")
    cols = [c for c in ["<=22", "23-26", "27-30", "31-34", "35+"] if c in piv]
    log("    " + "bucket".ljust(10) + "".join(c.rjust(10) for c in cols))
    for b in ["star", "regular", "fringe", "negative"]:
        if b not in piv.index:
            continue
        line = "    " + b.ljust(10)
        for c in cols:
            v, n = piv.loc[b, c], cnt.loc[b, c]
            line += (f"{v*100:7.1f}%" + f"({int(n):>4})" if pd.notna(v)
                     else "      --      ")
        log(line)

    for _ln in report_item_14(d, "SKATERS"):
        log(_ln)

    # ---- sensitivity: GP >= 1 population ------------------------------------
    # (v1.0 referenced build_transitions() locals here -- NameError on any
    # standalone run; the imported builders masked it. Fixed: rebuild.)
    w = pd.read_csv(F_WAR)
    w["syr"] = w["Season"].str.split("-").str[0].astype(int) + 2000
    w = w.groupby(["Player", "syr"], as_index=False).agg(GP=("GP", "sum"))
    present = set(zip(w["Player"], w["syr"]))
    q1 = w[(w["GP"] >= 1) & w["syr"].between(T_FIRST, T_LAST)]
    ex1 = np.mean([(p, t + 1) not in present
                   for p, t in zip(q1["Player"], q1["syr"])])
    log(f"\nsensitivity, GP>=1 population: {ex1*100:.2f}%/yr "
        f"(higher, as expected -- cup-of-coffee players churn out; the "
        f"GP>={MIN_GP} figure is the one that matches the priced population)")

    Path(OUT_LOG).write_text("\n".join(LOG), encoding="utf-8")
    log(f"\nrun log written: {OUT_LOG}")


if __name__ == "__main__":
    main()
