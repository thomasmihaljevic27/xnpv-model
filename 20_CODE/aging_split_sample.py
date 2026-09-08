"""
aging_split_sample.py -- split-sample stability check on the aging curve.

WHAT KARL IS ACTUALLY ASKING
----------------------------
The project defends the aging curve as a STABLE STRUCTURAL PARAMETER: how a
hockey player's production changes as he ages is a fact about human beings,
not about the 2019 salary cap, so fitting it on the whole panel and applying
it at every decision date is not look-ahead. That defence is currently
ASSERTED. This turns it into something TESTED.

The test: fit the age profile separately on an early era and a late era and
see whether they agree. If they do, the parameter is stable and using the
full panel is defensible. If they diverge, the curve is picking up something
era-specific and the whole no-look-ahead argument weakens.

WHAT IS COMPARED
----------------
Two things, because they can disagree:

1. THE AGE-DELTA CURVE. For every player seen at age a and again at a+1,
   the change in his per-82 WAR. Averaged by age and position, this is the
   raw aging signal the model is built on, measured without the model.
   Comparing it era to era is the cleanest possible version of the test.

2. THE MODEL'S OWN GLOBAL AGE PROFILE, which is what the projection leans
   on when a player has thin comparables. Two era-specific AgingModel
   instances are built and their internal profiles compared.

WHY WITHIN-PLAYER DELTAS AND NOT AGE-GROUP MEANS
-------------------------------------------------
Comparing the average 24-year-old to the average 32-year-old confuses aging
with SURVIVORSHIP: the 32-year-olds still playing are the ones who were good
enough to last, so the raw cross-section makes aging look far gentler than
it is. Taking each player's own change from one season to the next removes
that, because every observation is one man compared to himself.

Survivorship still bites at the point of EXIT (a player who falls off a
cliff leaves and contributes no delta), which is exactly why the project has
a separate exit hazard. This test inherits that limitation and does not try
to fix it.

INFERENCE
---------
Differences are tested by a player-clustered bootstrap: resample PLAYERS,
not player-seasons, because one player contributes many correlated rows and
treating them as independent would understate the standard errors.

STALENESS
---------
Runs against the read-only project mirror, which is two sessions behind and
does not include the Stage 1 aging_curve.py changes. Treat as indicative
and re-run locally.
"""

import numpy as np
import pandas as pd
import warnings

warnings.filterwarnings("ignore")

WAR_AGE = "C:/Users/thoma/OneDrive/Desktop/xNPV Data/WAR_with_age.csv"
MIN_GP = 20                      # matches the model's own panel filter
EARLY = (2007, 2015)             # season_start years, inclusive
LATE = (2016, 2025)


def load():
    """Panel of qualifying player-seasons with per-82 WAR and season year."""
    w = pd.read_csv(WAR_AGE)
    # "07-08" -> 2007. The Season column is a two-year label, so the first
    # half is the season start year.
    w["season_start"] = w["Season"].str.slice(0, 2).astype(int)
    w["season_start"] = np.where(w["season_start"] > 50,
                                 1900 + w["season_start"],
                                 2000 + w["season_start"])
    w = w[(w["GP"] >= MIN_GP) & w["age"].notna()].copy()
    w["w82"] = w["WAR"] / w["GP"] * 82.0
    w["posgrp"] = np.where(w["Position"].astype(str).str.upper().str.startswith("D"),
                           "D", "F")
    return w[["Player", "season_start", "age", "w82", "posgrp"]]


def deltas(panel):
    """One row per consecutive-age pair for the same player: the change in
    per-82 WAR from age a to age a+1."""
    p = panel.sort_values(["Player", "age"])
    p["next_age"] = p.groupby("Player")["age"].shift(-1)
    p["next_w82"] = p.groupby("Player")["w82"].shift(-1)
    d = p[p["next_age"] == p["age"] + 1].copy()
    d["delta"] = d["next_w82"] - d["w82"]
    return d


def era_profile(d, lo, hi, ages):
    """Mean age-delta by age within one era."""
    e = d[(d["season_start"] >= lo) & (d["season_start"] <= hi)]
    return e.groupby("age")["delta"].agg(["mean", "size"]).reindex(ages)


def boot_diff(d, ages, n=2000, seed=7):
    """Player-clustered bootstrap of (late mean - early mean) at each age."""
    rng = np.random.default_rng(seed)
    players = d["Player"].unique()
    idx = {p: g for p, g in d.groupby("Player")}
    out = []
    for _ in range(n):
        samp = pd.concat([idx[p] for p in rng.choice(players, len(players))])
        a = era_profile(samp, *EARLY, ages)["mean"]
        b = era_profile(samp, *LATE, ages)["mean"]
        out.append((b - a).values)
    return np.nanpercentile(np.array(out), [2.5, 97.5], axis=0)


def main():
    panel = load()
    d = deltas(panel)
    print(f"panel: {len(panel):,} qualifying player-seasons, "
          f"{panel.Player.nunique():,} players")
    print(f"usable consecutive-age deltas: {len(d):,}\n")

    for pos in ("F", "D"):
        dp = d[d["posgrp"] == pos]
        ages = list(range(20, 36))
        e = era_profile(dp, *EARLY, ages)
        l = era_profile(dp, *LATE, ages)
        lo, hi = boot_diff(dp, ages)
        print("=" * 74)
        print(f"POSITION {pos}   early {EARLY[0]}-{EARLY[1]}   late {LATE[0]}-{LATE[1]}")
        print("=" * 74)
        print(f"{'age':>4} {'early':>8} {'n':>5} {'late':>8} {'n':>5} "
              f"{'diff':>8} {'95% CI':>18}  flag")
        n_sig = 0
        for i, a in enumerate(ages):
            de, dl = e.loc[a, "mean"], l.loc[a, "mean"]
            if np.isnan(de) or np.isnan(dl):
                continue
            diff = dl - de
            sig = not (lo[i] <= 0 <= hi[i])
            n_sig += sig
            print(f"{a:>4} {de:>8.3f} {int(e.loc[a,'size']):>5} "
                  f"{dl:>8.3f} {int(l.loc[a,'size']):>5} {diff:>8.3f} "
                  f"[{lo[i]:>7.3f},{hi[i]:>7.3f}]  {'DIFFERS' if sig else ''}")
        print(f"\n  ages where the eras differ at 95%: {n_sig} of {len(ages)}\n")


if __name__ == "__main__":
    main()
