"""
pick_review_checks.py -- three checks raised by Thomas's comments on "Valuing Draft Picks" (2026-10-09).

1. DOES MOST OF A PICK'S VALUE COME FROM STARS? (comments 0 and 6: "you state this with no
   evidence"). Share of all drafted-skater surplus (pick_curve.py, adopted pricing) produced by the
   players who became stars under Bacon's definition (career WAR per 82 of 1.8+ F / 1.23+ D, with
   200+ NHL games; pick_star_and_rights_checks.py v1.1). Drafts 2007-2015, whose careers are mostly
   complete.
2. IS THERE A TREND IN THE DOLLAR SCALE ACROSS DRAFTS? (comments 16 and 18: "do we have any real
   reason to be using this Dollar Scale business? What if teams simply value draft picks
   consistently over time?"). The recorded test (p = 0.0045) showed only that drafts DIFFER; it never
   asked whether value drifts over time, which is the only thing that would bias a scale fitted on
   all drafts. Here: surplus = (b0 + b1 x (draft year - 2012)) x star probability, draft-year levels
   kept; b1 tested with robust and with draft-clustered errors, and with the two largest drafts
   (2015, 2016) left out. Also: the all-drafts scale with 2015 and 2016 left out.
3. HOW PREDICTABLE IS A TEAM'S DRAFT POSITION A YEAR OR TWO AHEAD? (comment 28: the round average for
   future picks needs its justification). Each team's place in the final regular-season standings
   (points percentage, worst first, the order the draft follows before the lottery) from games.csv,
   2017-18 to 2025-26, compared with its place one and two seasons later.

REPORT ONLY. Run from the repo root:  python 25_TESTS/pick_review_checks.py
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv

SCRIPT_VERSION = "pick_review_checks.py v1.0 (2026-10-09)"
print(SCRIPT_VERSION)
load_dotenv()
OUT, SRC = Path(os.environ["OUTPUT_DIR"]), Path(os.environ["SOURCE_DIR"])
print(f"  pick_curve_log: {(OUT / 'pick_curve_log.txt').read_text(encoding='utf-8').splitlines()[0]}")

# ---- 1. stars' share of surplus ----------------------------------------------------------------
pc = pd.read_csv(OUT / "pick_curve_players.csv")
st = pd.read_csv(OUT / "pick_star_and_rights_checks.csv")[["draftYear", "pick", "star", "nhler"]]
m = pc.merge(st, on=["draftYear", "pick"], how="inner", validate="one_to_one")
m = m[m["draftYear"] <= 2015]
tot = m["surplus"].sum()
print(f"\n1. STARS' SHARE OF SURPLUS (skaters, 2007-2015 drafts: {len(m):,} picks, total ${tot / 1e6:,.1f}M)")
for lab, g in (("stars", m[m["star"]]), ("NHL regulars who were not stars (200+ games)", m[m["nhler"] & ~m["star"]]),
               ("under 200 NHL games", m[~m["nhler"]])):
    print(f"  {lab:46s} {len(g):5d} picks ({100 * len(g) / len(m):4.1f}%)  {100 * g['surplus'].sum() / tot:6.1f}% of surplus")
for lo, hi in ((1, 10), (11, 32), (33, 217)):
    g = m[m["pick"].between(lo, hi)]
    print(f"  picks {lo}-{hi}: stars are {100 * g['star'].mean():.1f}% of picks and {100 * g.loc[g['star'], 'surplus'].sum() / g['surplus'].sum():.1f}% of surplus")

# ---- 2. trend in the scale ------------------------------------------------------------------------
def fit(frame, trend=True, cluster=False):
    yrs = frame["draftYear"].values
    cl = sorted(set(yrs))
    Y = [(yrs == c).astype(float) - (yrs == cl[-1]).astype(float) for c in cl[:-1]]
    cols = [frame["p_star"].values] + ([frame["p_star"].values * (yrs - 2012)] if trend else []) + Y
    mod = sm.OLS(frame["surplus"].values / 1e6, np.column_stack(cols))
    return mod.fit(cov_type="cluster", cov_kwds={"groups": yrs}) if cluster else mod.fit(cov_type="HC1")


print("\n2. TREND IN THE SCALE ($M per 100% star probability, per draft year)")
for lab, frame in (("all drafts", pc), ("without 2015", pc[pc["draftYear"] != 2015]),
                   ("without 2015 and 2016", pc[~pc["draftYear"].isin([2015, 2016])])):
    r = fit(frame)
    rc = fit(frame, cluster=True)
    print(f"  {lab:22s} trend {r.params[1]:+.2f} a year (robust se {r.bse[1]:.2f}, p {r.pvalues[1]:.3f}; "
          f"clustered by draft se {rc.bse[1]:.2f}, p {rc.pvalues[1]:.3f})")
for lab, frame in (("all eleven drafts", pc), ("without 2015 and 2016", pc[~pc["draftYear"].isin([2015, 2016])])):
    r = fit(frame, trend=False)
    print(f"  constant scale, {lab:22s} {r.params[0]:.2f} (se {r.bse[0]:.2f})")

# ---- 3. persistence of draft position ----------------------------------------------------------------
g = pd.read_csv(SRC / "games.csv")
g = g[g["game_type"] == 2]
rows = []
for season, s in g.groupby("season"):
    rec = {}
    for r in s.itertuples():
        hw = r.home_score > r.away_score
        for team, won in ((r.home_team, hw), (r.away_team, not hw)):
            w, ot, gp = rec.get(team, (0, 0, 0))
            rec[team] = (w + won, ot + ((not won) and r.last_period in ("OT", "SO")), gp + 1)
    t = pd.DataFrame([(k, *v) for k, v in rec.items()], columns=["team", "w", "otl", "gp"])
    t["pct"] = (2 * t["w"] + t["otl"]) / (2 * t["gp"])
    t = t.sort_values(["pct", "w"]).reset_index(drop=True)
    t["place"] = t.index + 1                      # 1 = worst record = first in the draft before the lottery
    t["season"] = int(str(season)[:4])
    rows.append(t[["season", "team", "place"]])
pl = pd.concat(rows)
pl["team"] = pl["team"].replace({"UTA": "ARI"})
print(f"\n3. DRAFT POSITION FROM FINAL STANDINGS, {pl['season'].min()}-{pl['season'].max() + 1}: "
      f"{pl['season'].nunique()} seasons")
out = {}
for k in (1, 2):
    nxt = pl.assign(season=pl["season"] - k).rename(columns={"place": f"place_{k}"})
    j = pl.merge(nxt, on=["season", "team"])
    diff = (j[f"place_{k}"] - j["place"]).abs()
    out[k] = j
    print(f"  {k} season(s) later: {len(j)} team-pairs; correlation {np.corrcoef(j['place'], j[f'place_{k}'])[0, 1]:.2f}; "
          f"median move {diff.median():.0f} places, {int((diff > 8).sum())} of {len(j)} moved more than 8")
    for lo, hi in ((1, 5), (6, 16), (17, 32)):
        s = j[j["place"].between(lo, hi)][f"place_{k}"]
        print(f"    teams placed {lo}-{hi}: later place mean {s.mean():.1f}, 10th-90th percentile {s.quantile(.1):.0f}-{s.quantile(.9):.0f}")
pd.concat([out[1].assign(gap=1).rename(columns={"place_1": "later"}),
           out[2].assign(gap=2).rename(columns={"place_2": "later"})]).to_csv(OUT / "pick_slot_persistence.csv", index=False)
print(f"\nwrote {OUT / 'pick_slot_persistence.csv'}")
