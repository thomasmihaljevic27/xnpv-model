"""
pick_choices_current.py -- Appendix C's pick-model choices re-measured on the pick curve as it runs (the arbitration cost).

WHY: "Valuing Players, Draft Picks, and Prospects" v4 reported five of Appendix C's effects as measured on October 9, 2026
under the qualifying-offer chain, a cost rule no longer in any part of the model (Thomas, comment 37 of round 2). This
re-measures each from the current pick curve's own outputs, so the appendix describes the model as it runs.

INPUTS (read only): OUTPUT_DIR/pick_curve_players.csv and pick_curve_seasons.csv (pick_curve.py v1.11, the adopted
arbitration cost; `surplus` is the career net present value at the 2025-26 cap, lapsed rights zeroed), and
draft_pick_linkage.csv (birthdates, for the slide rule). Deceased draftees are left out of every fit, as in pick_curve.

THE FIT: career net present value on the star probability, no intercept, least squares, on the 2,316 players
(GUARD: reproduces pick_curve's star value). "The mean pick" is the star value times the mean star probability of the
2,316 picks.

EFFECTS
  1. Brief call-ups as full seasons: each season under 10 NHL games unscaled (its value and cost divided by games / 82).
  2. Entry-level slides (CBA 9.1(d)), APPROXIMATE: an entry-level season in which the player was 18 or 19 on September 15
     and played under 10 NHL games does not use up a year; each such season moves the first played season after the
     entry-level contract to the entry-level cost (his class's maximum, scaled as that season is). The qualifying-offer
     and arbitration chain after it is not re-run, and a season with no NHL game, which costs nothing either way, is not
     counted. Reported as the change in the star value.
  3. Careers that lost money floored at zero: each player's career value max(0, value), lapsed rights still zero.
  4. Rights that lapsed: the lapsed players' share of drafted skaters' career value before the rights rule, positive
     careers (the share of what a pick could have returned), and of the signed total.
  5. A separate goaltender star value: the fit on goaltenders alone, at the first pick's star probability.

Run from the repo root:  python 25_TESTS/pick_choices_current.py
"""

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

SCRIPT_VERSION = "pick_choices_current.py v1.0 (2026-10-22)"
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", ROOT / "30_OUTPUT"))

LOG = []


def log(s=""):
    print(s)
    LOG.append(s)


log(SCRIPT_VERSION)
for f in ("pick_curve_scales.csv", "pick_curve_players.csv", "pick_curve_seasons.csv", "draft_pick_linkage.csv"):
    p = OUTPUT_DIR / f
    log(f"  input {p}  (modified {pd.Timestamp(p.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M})")

SC = pd.read_csv(OUTPUT_DIR / "pick_curve_scales.csv").set_index("scale_kind")
STAR_LOCK = float(SC.loc["main", "scale_M"])   # pick_curve.py's star value, $M at the 2025-26 cap; GUARD to 1e-6
P = pd.read_csv(OUTPUT_DIR / "pick_curve_players.csv")
S = pd.read_csv(OUTPUT_DIR / "pick_curve_seasons.csv")
L = pd.read_csv(OUTPUT_DIR / "draft_pick_linkage.csv", usecols=["draftYear", "overallPickNumber", "birthDate"])
L = L.rename(columns={"overallPickNumber": "pick"})
P = P[~P["excluded_deceased"]].copy()
assert len(P) == 2316, len(P)                                              # GUARD: the fit's players
LAPSED = P["route"].isin(["lapsed", "drafted twice (earlier pick)"])


def star(y, x):
    """No-intercept least squares slope, $M."""
    return float((x * y).sum() / (x * x).sum()) / 1e6


b0 = star(P["surplus"], P["p_star"])
log(f"\nstar value: ${b0:.6f}M (pick_curve v1.11: ${STAR_LOCK:.6f}M)")
assert abs(b0 - STAR_LOCK) < 1e-6, b0                                      # GUARD: the adopted fit reproduced
mean_ps = P["p_star"].mean()
log(f"  the mean pick: star value x mean star probability ({mean_ps:.5f}) = ${b0 * mean_ps:.3f}M")

# the seasons file's surplus is each season's value less cost at the 2025-26 cap; per player it sums to the
# value before the rights rule (GUARD)
key = ["draftYear", "pick"]
tot = S.groupby(key)["surplus_2025_cap"].sum().rename("from_seasons")
chk = P.set_index(key)[["surplus_before_rights"]].join(tot).fillna(0.0)
gap = (chk["surplus_before_rights"] - chk["from_seasons"]).abs().max()
log(f"  guard: seasons sum to each player's value before the rights rule (largest gap ${gap:.2e})")
assert gap < 1.0


def refit(season_values):
    """Star value with each player's career rebuilt from per-season values (a Series on S's index)."""
    per = season_values.groupby([S["draftYear"], S["pick"]]).sum()
    v = P.set_index(key).index.map(lambda k: per.get(k, 0.0))
    v = pd.Series(np.asarray(v, dtype=float), index=P.index)
    v[LAPSED] = 0.0
    return star(v, P["p_star"]), v


res = []

# 1. brief call-ups as full seasons
full = S["surplus_2025_cap"] / S["games_scale"]
b1, _ = refit(full)
n_cameo = int((S["games_scale"] < 1).sum())
log(f"\n1. brief call-ups as full seasons ({n_cameo} seasons under 10 games): star value ${b1:.3f}M, "
    f"mean pick ${b1 * mean_ps:.2f}M against ${b0 * mean_ps:.2f}M ({100 * (b1 / b0 - 1):+.1f}%)")
res.append({"choice": "brief call-ups", "star_M": b1, "mean_pick_M": b1 * mean_ps, "pct": 100 * (b1 / b0 - 1)})

# 2. entry-level slides, approximate
S2 = S.merge(L, left_on=["draftYear", "pick"], right_on=["draftYear", "pick"], how="left")
assert S2["birthDate"].notna().all()
bd = pd.to_datetime(S2["birthDate"])
age = S2["season"] - bd.dt.year - ((bd.dt.month > 9) | ((bd.dt.month == 9) & (bd.dt.day > 15))).astype(int)
S2["slides"] = S2["in_entry_level"] & (S2["gp"] < 10) & (age <= 19)
elc_max = (S2.loc[S2["in_entry_level"], "cost_$"] / S2.loc[S2["in_entry_level"], "games_scale"]).groupby(S2["draftYear"]).max()
cap_now = float((S2["surplus_2025_cap"] / (S2["value_share"] - S2["cost_share"])).replace([np.inf, -np.inf], np.nan).median())
adj = S2["surplus_2025_cap"].copy()
n_slid, n_moved = 0, 0
for k, g in S2.groupby(key):
    ns = int(g["slides"].sum())
    if ns == 0:
        continue
    n_slid += 1
    post = g[~g["in_entry_level"]].sort_values("season")
    last_elc = int(g.loc[g["in_entry_level"], "season"].max())
    post = post[post["season"] <= last_elc + ns]                    # the seasons the extended contract covers, by calendar
    for i, r in post.iterrows():
        elc_cost = elc_max[k[0]] / r["cap"] * r["games_scale"]
        adj[i] = (r["value_share"] - elc_cost) * cap_now
        n_moved += 1
b2, _ = refit(pd.Series(adj.values, index=S.index))
log(f"\n2. entry-level slides (approximate): {n_slid} players have a season that slides; {n_moved} later played seasons "
    f"move to the entry-level cost; star value ${b2:.3f}M ({100 * (b2 / b0 - 1):+.2f}%)")
res.append({"choice": "entry-level slides", "star_M": b2, "mean_pick_M": b2 * mean_ps, "pct": 100 * (b2 / b0 - 1),
            "players": n_slid, "seasons": n_moved})

# 3. careers that lost money floored at zero
v3 = P["surplus"].clip(lower=0.0)
b3 = star(v3, P["p_star"])
n_neg = int((P["surplus"] < 0).sum())
log(f"\n3. careers floored at zero ({n_neg} negative careers): star value ${b3:.3f}M ({100 * (b3 / b0 - 1):+.1f}%)")
res.append({"choice": "floored at zero", "star_M": b3, "pct": 100 * (b3 / b0 - 1), "negative": n_neg})

# 4. rights that lapsed
sk = ~P["is_goalie"]
pos = P["surplus_before_rights"].clip(lower=0.0)
share_pos = float(pos[sk & LAPSED].sum() / pos[sk].sum())
share_net = float(P.loc[sk & LAPSED, "surplus_before_rights"].sum() / P.loc[sk, "surplus_before_rights"].sum())
log(f"\n4. lapsed rights ({int((sk & LAPSED).sum())} skaters): {100 * share_pos:.1f}% of drafted skaters' positive career "
    f"value before the rights rule; {100 * share_net:.1f}% of the net total")
res.append({"choice": "lapsed rights", "share_positive": share_pos, "share_net": share_net})

# 5. a separate goaltender star value
g = P[P["is_goalie"]]
bg = star(g["surplus"], g["p_star"])
ps1 = float(P.loc[P["pick"] == 1, "p_star"].iloc[0])
log(f"\n5. goaltenders alone ({len(g)}): star value ${bg:.2f}M; at the first pick's star probability ({ps1:.3f}), "
    f"${bg * ps1:.1f}M; skaters alone ${star(P.loc[sk, 'surplus'], P.loc[sk, 'p_star']):.2f}M")
res.append({"choice": "goaltender star value", "star_M": bg, "first_pick_M": bg * ps1})

pd.DataFrame(res).to_csv(OUTPUT_DIR / "pick_choices_current.csv", index=False)
(OUTPUT_DIR / "pick_choices_current_log.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
log("\nwrote pick_choices_current.csv and pick_choices_current_log.txt")
