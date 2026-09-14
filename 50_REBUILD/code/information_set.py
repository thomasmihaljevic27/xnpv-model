"""information_set.py -- what was knowable on a given date.

EXPERIMENTAL (50_REBUILD). Rebuild plan Phase 0, item 3.

THE RULE THIS FILE ENFORCES
    A valuation made on date d may use only what a team could have read on
    date d. In the production chain that rule is a property of one lookup
    ("the lookup below is structurally incapable of seeing season t"). Here it
    is an object: every model receives an InformationSet and has no other way
    to reach the data, so a model CANNOT see a future season even by mistake.
    That is the difference between a convention and a guarantee, and it is why
    the harness is built before any model is compared on it.

WHAT "COMPLETE" MEANS, AND WHY IT IS NOT THE FINAL HORN
    Two dates matter and they are not the same:
      season end        the last regular-season game was played
      availability      the vendor's completed-season WAR could be read
    Bacon's WAR is a season-level export; it does not exist at the final horn.
    Treating it as available that night would let a July valuation read a
    season whose numbers were not published until later. AVAILABILITY_LAG_DAYS
    carries that gap explicitly, defaults to a conservative 30 days, and is a
    declared sensitivity rather than a silent zero.

    Where a season's end date is not verified below, the fallback is 30 June
    of the ending year -- later than any real regular season, so the fallback
    can only ever make information arrive LATER than it truly did. A wrong
    guess in that direction costs realism; a wrong guess the other way is a
    look-ahead leak. The asymmetry is deliberate.

WHAT IS NOT IMPLEMENTED HERE
    The contract side. Contract state, signing dates and the D28 extension
    rule need the PuckPedia export, which is confidential vendor data and is
    not present in every checkout. contracts_known_at() raises a clear error
    rather than returning an empty frame that a caller could mistake for "this
    player had no contract". The season side below is complete and is what
    Phases 1-3 need; the contract side is required from Phase 4.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C

SCRIPT_VERSION = "1.0"

# Last day of each NHL REGULAR season, by season start year. `True` marks a
# date carried deliberately; anything absent falls back to 30 June (see above).
#   2012-13  lockout, 48 games, began 19 January 2013
#   2019-20  the regular season was never completed -- play was suspended on
#            12 March 2020 and the remaining regular-season games were never
#            played, so the suspension date IS this season's end. The D20
#            proration exists for the same reason.
#   2020-21  56 games, began 13 January 2021
SEASON_END: dict[int, date] = {
    2007: date(2008, 4, 6), 2008: date(2009, 4, 12), 2009: date(2010, 4, 11),
    2010: date(2011, 4, 10), 2011: date(2012, 4, 7), 2012: date(2013, 4, 28),
    2013: date(2014, 4, 13), 2014: date(2015, 4, 11), 2015: date(2016, 4, 10),
    2016: date(2017, 4, 9), 2017: date(2018, 4, 7), 2018: date(2019, 4, 6),
    2019: date(2020, 3, 12), 2020: date(2021, 5, 19), 2021: date(2022, 4, 29),
    2022: date(2023, 4, 13), 2023: date(2024, 4, 18), 2024: date(2025, 4, 17),
}

AVAILABILITY_LAG_DAYS = 30


def season_available_from(syr: int, lag_days: int = AVAILABILITY_LAG_DAYS) -> date:
    """The first date a completed season's WAR may be read."""
    end = SEASON_END.get(syr) or date(syr + 1, 6, 30)
    return end + timedelta(days=lag_days)


def seasons_complete_at(d: date, lag_days: int = AVAILABILITY_LAG_DAYS) -> list[int]:
    """Season start years whose completed WAR was readable on d, newest first."""
    return sorted((s for s in range(C.FIRST_SOURCE_SEASON, C.LAST_SOURCE_SEASON + 1)
                   if season_available_from(s, lag_days) <= d), reverse=True)


def decision_date_for_page(t0: int) -> date:
    """The canonical decision date for valuation season t0.

    1 July of t0: the opening of free agency, the date the production chain's
    season-start valuations implicitly stand at, and comfortably after every
    verified season end plus the availability lag. A trade-deadline valuation
    is a different decision date on the same page and is built by passing that
    date directly -- the harness never assumes 1 July.
    """
    return date(t0, 7, 1)


@dataclass(frozen=True)
class InformationSet:
    """Everything knowable on `as_of`, and nothing else.

    Frozen (immutable) on purpose: a model handed one cannot reach around it
    to widen its own information. `seasons` is the table already filtered to
    complete-and-available seasons, so a model that simply uses everything it
    is given is automatically look-ahead clean.
    """
    as_of: date
    t0: int                      # the valuation season this date sits before
    seasons: pd.DataFrame        # season table, complete seasons only
    lag_days: int

    @property
    def latest_season(self) -> int:
        return int(self.seasons["syr"].max())

    def history(self, career_key: str) -> pd.DataFrame:
        return self.seasons[self.seasons["career_key"] == career_key]

    def trailing(self, n: int) -> pd.DataFrame:
        """The most recent n complete seasons, the window an anchor reads."""
        keep = sorted(self.seasons["syr"].unique())[-n:]
        return self.seasons[self.seasons["syr"].isin(keep)]

    def contracts_known_at(self):
        raise NotImplementedError(
            "The contract side of the information set is not built yet "
            "(rebuild plan Phase 4). It needs the PuckPedia export, which is "
            "confidential vendor data and absent from checkouts without it. "
            "Raising rather than returning an empty frame: an empty frame "
            "would read as 'this player has no contract', which is a "
            "different and wrong claim.")


def build(table: pd.DataFrame, as_of: date, t0: int | None = None,
          lag_days: int = AVAILABILITY_LAG_DAYS) -> InformationSet:
    """Cut the season table down to what was readable on `as_of`.

    This is the only sanctioned way to give a model data. The filter is on
    season start year, and the mapping from year to availability runs through
    season_available_from(), so changing the lag changes every model at once
    and no model can opt out of it.
    """
    complete = seasons_complete_at(as_of, lag_days)
    sub = table[table["syr"].isin(complete)].copy()
    if t0 is None:
        t0 = as_of.year if as_of.month >= 7 else as_of.year - 1
    # The one invariant worth asserting out loud: the valuation season itself
    # is never in the information set. Every look-ahead incident in this
    # project's history would have been caught by this line.
    assert t0 not in set(sub["syr"]), (
        f"season {t0} is in an information set dated {as_of} -- that is the "
        "season being valued; a model must never see it")
    return InformationSet(as_of=as_of, t0=t0, seasons=sub, lag_days=lag_days)


def self_test() -> None:
    """The plan's Phase 0 acceptance test in miniature: removing everything
    after a decision date must leave that date's information set unchanged."""
    from player_season_table import build as build_table
    t = build_table(verbose=False)

    for t0 in (2015, 2020, 2021, 2025):
        d = decision_date_for_page(t0)
        full = build(t, d)
        truncated = build(t[t["syr"] < t0], d)
        assert full.seasons.shape == truncated.seasons.shape, (
            f"page {t0}: dropping seasons >= t0 changed the information set, "
            "so something after the decision date was reaching it")
        assert full.latest_season == t0 - 1
        C.log(f"  page {t0}: as-of {d}, sees {len(full.seasons)} season rows "
              f"through {full.latest_season}; truncation test PASS")

    # 2019-20 is the case worth checking by hand: the season ended on the
    # 12 March suspension, so a 1 July 2020 valuation reads it, while a
    # valuation the previous autumn does not.
    assert 2019 in seasons_complete_at(date(2020, 7, 1))
    assert 2019 not in seasons_complete_at(date(2019, 12, 1))
    C.log("  2019-20 suspension handled: readable 2020-07-01, not 2019-12-01")

    # And the lag does what it says: the last 2024-25 game was 17 April 2025,
    # so a 1 May valuation must NOT see it under a 30-day lag.
    assert 2024 not in seasons_complete_at(date(2025, 5, 1))
    assert 2024 in seasons_complete_at(date(2025, 7, 1))
    C.log(f"  availability lag of {AVAILABILITY_LAG_DAYS} days binds: 2024-25 "
          "unreadable on 2025-05-01, readable on 2025-07-01")

    unverified = [s for s in range(C.FIRST_SOURCE_SEASON, C.LAST_SOURCE_SEASON + 1)
                  if s not in SEASON_END]
    C.log(f"  season-end dates: {len(SEASON_END)} carried, "
          f"{len(unverified)} on the 30 June fallback {unverified}")


if __name__ == "__main__":
    C.banner("information_set.py", SCRIPT_VERSION)
    C.log("Frozen-information self test (rebuild plan, Phase 0 item 3)")
    self_test()
    C.log("")
    C.log("  ALL PASS")
    C.write_log("information_set_run_log.txt")
