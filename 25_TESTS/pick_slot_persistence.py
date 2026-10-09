"""
pick_slot_persistence.py -- how well does a team's draft slot predict its slot a year or two later?

WHY (Thomas, 2026-10-09): a pick for a later draft is valued at its round's average star probability
(decided in the 2026-10-09 meeting and kept on review). The document must show the evidence; the
persistence chart reviewed in that meeting is not in the repo ("im sure you can recreate the data").

DATA: the cached NHL draft records, OUTPUT_DIR/draft_raw/draft_YYYY.json (draft_pick_linkage.py),
drafts 2005-2026. A team's OWN first-round slot is the first-round pick whose ownership history
(`teamPickHistory`, e.g. "LAK-BOS") starts with that team; franchises joined across moves (ATL = WPG,
PHX = ARI = UTA). A team with no own first-round pick that year (traded picks are still its own;
forfeited picks are not) has no slot. Actual draft slots, so the lottery and playoff results are in.

REPORTED (report only):
  * correlation between a team's slot and its slot one and two drafts later, and how far it moves;
  * for teams that picked 1-5, 6-10, 11-16, 17-24, 25-32: where they pick one and two drafts later
    (mean, 10th and 90th percentiles);
  * WHAT THE ROUND AVERAGE COSTS: for a future first-round pick, the average star probability over the
    slots the team actually went on to pick at, given its current band, against the round average
    (Bacon's star probability, draft_slot_baseline.csv), in dollars at the main star value
    (pick_curve_scales.csv).
OUTPUT: OUTPUT_DIR/pick_slot_persistence.csv (one row per team and draft pair).

Run from the repo root:  python 25_TESTS/pick_slot_persistence.py
"""

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

SCRIPT_VERSION = "pick_slot_persistence.py v1.0 (2026-10-09)"
print(SCRIPT_VERSION)
load_dotenv()
OUT, SRC = Path(os.environ["OUTPUT_DIR"]), Path(os.environ["SOURCE_DIR"])
FR = {"ATL": "WPG", "PHX": "ARI", "UTA": "ARI"}

rows = []
for f in sorted((OUT / "draft_raw").glob("draft_*.json")):
    y = int(f.stem.split("_")[1])
    for r in json.loads(f.read_text(encoding="utf-8"))["data"]:
        if r["roundNumber"] != 1 or not r.get("teamPickHistory"):
            continue
        own = r["teamPickHistory"].split("-")[0].strip()
        rows.append({"year": y, "team": FR.get(own, own), "slot": r["overallPickNumber"]})
s = pd.DataFrame(rows).drop_duplicates(["year", "team"])
print(f"  own first-round slots: {len(s)} team-drafts, drafts {s['year'].min()}-{s['year'].max()}")

bacon = pd.read_csv(SRC / "draft_slot_baseline.csv").set_index("draft_pick")["p_star"]
sc = pd.read_csv(OUT / "pick_curve_scales.csv")
STAR = float(sc.loc[sc["scale_kind"] == "main", "scale_M"].iloc[0])
print(f"  star value (main): {STAR:.2f}  [{(OUT / 'pick_curve_log.txt').read_text(encoding='utf-8').splitlines()[0]}]")
teams_in = s.groupby("year")["team"].size()

pairs = []
for k in (1, 2):
    later = s.assign(year=s["year"] - k).rename(columns={"slot": "later"})
    j = s.merge(later, on=["year", "team"])
    j["gap"] = k
    pairs.append(j)
    d = (j["later"] - j["slot"]).abs()
    print(f"\n{k} DRAFT(S) LATER: {len(j)} team-pairs; correlation {np.corrcoef(j['slot'], j['later'])[0, 1]:.2f}; "
          f"median move {d.median():.0f} slots; moved more than 10: {int((d > 10).sum())} of {len(j)}")
    # round average of the first round, by the later draft's number of first-round picks
    j["round_avg_star"] = j["year"].add(k).map(lambda yy: float(np.mean([bacon[i] for i in range(1, int(teams_in.get(yy, 32)) + 1)])))
    j["later_star"] = j["later"].map(bacon)
    for lo, hi in ((1, 5), (6, 10), (11, 16), (17, 24), (25, 32)):
        g = j[j["slot"].between(lo, hi)]
        print(f"  picked {lo:2d}-{hi:2d} ({len(g):3d}): later slot mean {g['later'].mean():5.1f}, "
              f"10th-90th {g['later'].quantile(.1):3.0f}-{g['later'].quantile(.9):3.0f}; value of that later pick "
              f"${STAR * g['later_star'].mean():5.2f}M against the round average ${STAR * g['round_avg_star'].mean():5.2f}M")
pd.concat(pairs).to_csv(OUT / "pick_slot_persistence.csv", index=False)
print(f"\nwrote {OUT / 'pick_slot_persistence.csv'}")
