"""
slot_curve.py -- the draft yield curve as a per-pick price, plus the slot
conventions for picks whose number is not yet known.

SCRIPT_VERSION = 2.0  (2026-09-28)

RECREATED 2026-09-28. The July 2026 version (listed in 01_Draft_Model_Sequence.md
as an existing artifact) could not be found in git, Dropbox, the archive or any
local transcript, and was probably written in a pre-migration chat. This
version is rebuilt from the recorded conventions, not copied from the old code.

WHAT IT GIVES YOU
-----------------
slot_value(overall)           curve value of one pick number, in cap share
                              (Rule A, mean_share_A), read off the locked banded
                              curve in draft_yield_curve.csv. Multiply by a
                              season's cap ceiling for dollars.
round_mean_value(year, rnd)   the round-mean convention: the average slot_value
                              over every pick number in that round of that draft.
own_slot_overall(team, year, rnd, as_of)
                              the team-own-slot convention (decided 2026-09-28):
                              a pick whose number is not yet known is assumed
                              to land where its ORIGINAL team picked in its own
                              slot in the most recent draft held before the
                              trade date. A team that picked 20th in 2025 and
                              trades its 2026 first gives up an assumed 20th.

WHAT IT ASSUMES (each one a place a result could move)
------------------------------------------------------
- The curve is the banded one (1, 2, 3-5, 6-10, 11-20, 21-32, 33-50, 51-100,
  101-150, 151-224). The break test decided on 2026-09-28 will replace the
  bands; only CURVE_PATH / _band_share need to change here.
- Pick numbers above the last band (2005 had 230 picks) take the last band.
- "The original team" is the first code in the NHL Records teamPickHistory
  chain (e.g. "TOR-SJS-STL" is Toronto's pick). The trade export's
  draft_pick_team is mapped onto NHL codes (NAS->NSH, WAS->WSH) and the
  Arizona/Utah franchise is one team (ARI, PHX, UTA).
- The team's position is its pick-in-round in the most recent draft's FIRST
  round, applied to every round (a team picking 20th picks about 20th in each
  round). If it had no first-round pick of its own that year (forfeited), its
  own second-round position is used; failing that, mid-round.
- Teams per round: 30 through 2016, 31 for 2017-2020 (Vegas), 32 from 2021
  (Seattle). Compensatory picks are ignored when converting a round position
  into an overall number.
- Only drafts held BEFORE the trade date are read, so the convention never
  sees the draft it is predicting.
"""

import glob
import json
import os
from functools import lru_cache

import pandas as pd
from dotenv import load_dotenv

load_dotenv()
SCRIPT_VERSION = "2.0"

OUTPUT_DIR = os.environ["OUTPUT_DIR"]
CURVE_PATH = os.path.join(OUTPUT_DIR, "draft_yield_curve.csv")
DRAFT_RAW = os.path.join(OUTPUT_DIR, "draft_raw")

# PuckPedia -> NHL Records team codes, and franchises that changed code.
PP_TO_NHL = {"NAS": "NSH", "WAS": "WSH"}
FRANCHISE = {"PHX": "ARI", "UTA": "ARI", "ARI": "ARI", "ATL": "WPG"}


def franchise(code: str) -> str:
    code = PP_TO_NHL.get(str(code), str(code))
    return FRANCHISE.get(code, code)


def teams_in_draft(year: int) -> int:
    return 30 if year <= 2016 else (31 if year <= 2020 else 32)


@lru_cache(maxsize=1)
def _curve() -> pd.DataFrame:
    c = pd.read_csv(CURVE_PATH)
    lo_hi = c["bucket"].str.split("-", expand=True).astype(int)
    c["lo"], c["hi"] = lo_hi[0], lo_hi[1]
    return c.sort_values("lo").reset_index(drop=True)


def slot_value(overall: int) -> float:
    """Rule A curve value (cap share) of one pick number."""
    c = _curve()
    o = int(overall)
    hit = c[(c["lo"] <= o) & (c["hi"] >= o)]
    if hit.empty:
        return float(c.iloc[-1]["mean_share_A"]) if o > c["hi"].max() else float("nan")
    return float(hit.iloc[0]["mean_share_A"])


@lru_cache(maxsize=1)
def _draft_records() -> pd.DataFrame:
    rows = []
    for f in sorted(glob.glob(os.path.join(DRAFT_RAW, "draft_*.json"))):
        with open(f) as fh:
            rows += json.load(fh)["data"]
    d = pd.DataFrame(rows)
    d["draftDate"] = pd.to_datetime(d["draftDate"])
    d["orig_team"] = d["teamPickHistory"].str.split("-").str[0].map(franchise)
    return d


def draft_date(year: int) -> pd.Timestamp | None:
    d = _draft_records()
    s = d.loc[d["draftYear"] == year, "draftDate"]
    return s.iloc[0] if len(s) else None


def picks_in_round(year: int, rnd: int) -> list[int]:
    """Overall numbers in one round. Held drafts: from the record. Future
    drafts: teams_in_draft(year) consecutive numbers."""
    d = _draft_records()
    s = d.loc[(d["draftYear"] == year) & (d["roundNumber"] == rnd), "overallPickNumber"]
    if len(s):
        return sorted(s.astype(int).tolist())
    n = teams_in_draft(year)
    return list(range((rnd - 1) * n + 1, rnd * n + 1))


def round_mean_value(year: int, rnd: int) -> float:
    vals = [slot_value(o) for o in picks_in_round(year, rnd)]
    return sum(vals) / len(vals)


def own_slot_overall(team: str, year: int, rnd: int, as_of) -> tuple[int, str]:
    """Team-own-slot convention. Returns (assumed overall number, how it was found)."""
    d = _draft_records()
    as_of = pd.Timestamp(as_of)
    held = d[d["draftDate"] < as_of]
    if held.empty:
        raise ValueError(f"no draft held before {as_of.date()}")
    last = held["draftYear"].max()
    t = franchise(team)
    mine = held[(held["draftYear"] == last) & (held["orig_team"] == t)]
    how = f"own R1 position in {last}"
    pos = mine.loc[mine["roundNumber"] == 1, "pickInRound"]
    if pos.empty:
        pos = mine.loc[mine["roundNumber"] == 2, "pickInRound"]
        how = f"own R2 position in {last} (no own R1)"
    n = teams_in_draft(int(year))
    if pos.empty:
        p, how = (n + 1) // 2, f"mid-round (no own R1/R2 in {last})"
    else:
        p = min(int(pos.iloc[0]), n)
    return (int(rnd) - 1) * n + p, how


if __name__ == "__main__":
    print(f"slot_curve.py SCRIPT_VERSION {SCRIPT_VERSION}")
    print("pick 1:", slot_value(1), "| pick 20:", slot_value(20), "| pick 200:", slot_value(200))
    print("round-mean 2019 R1:", round(round_mean_value(2019, 1), 5))
    print("own slot, CBJ 2020 R1 as of 2019-02-22:", own_slot_overall("CBJ", 2020, 1, "2019-02-22"))
