"""
trade_page.py -- the valuation page of a trade: which season's page values an asset traded on a given date.

DECIDED (Thomas, 2026-10-14): "Value trades made after the regular season ends (June) on the next season's page,
for players, prospects and picks alike."

  page(date) = the season starting July 1 on or before the date (the trade season, as before), PLUS ONE when the
               date is after that season's last regular-season game.

  WHY: a trade after the regular season was valued on the page of the season just ended, as of July 1 of that
  season, so its value still counted the season already played (a June 2018 trade of Dougie Hamilton counted his
  2017-18 cap hit and production). The next page reads every regular season through the one just completed, all
  of it played before the trade: no look-ahead. The page's date is July 1, after the trade; anything signed between
  the trade and that July 1 is reported by the callers (it would be known to the page, not the trade).

  The last regular-season game per season: games.csv (game_type 2), 2017-18 on (2019-20: March 11, 2020, when the
  season was paused). A season without games in the file: April 20 of its ending year.

Used by prospect_values.py, traded_player_values.py, page_2017_values.py, contracts_2017.py, buried_contract_values.py,
rights_values.py (season_left_share, 2026-10-19)
and trade_asset_values.py (which also gives each traded pick its page; no pick value depends on it, and
traded_pick_values.py does not record it: corrected 2026-10-18). Import and call page(date).
"""

import os
from functools import lru_cache
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

load_dotenv()
SOURCE_DIR = Path(os.environ["SOURCE_DIR"])


@lru_cache(maxsize=1)
def regular_season_end() -> dict:
    """{season start year: date of its last regular-season game} from games.csv."""
    g = pd.read_csv(SOURCE_DIR / "games.csv", usecols=["season", "game_type", "game_date"])
    g = g[g["game_type"] == 2]
    g["syr"] = g["season"].astype(str).str[:4].astype(int)
    return pd.to_datetime(g["game_date"]).groupby(g["syr"]).max().to_dict()


def trade_season(date) -> int:
    """The season starting July 1 on or before the date."""
    d = pd.Timestamp(date)
    return d.year if d.month >= 7 else d.year - 1


def page(date) -> int:
    """The valuation page: the trade season, or the next one for a trade after its last regular-season game."""
    d, s = pd.Timestamp(date), trade_season(date)
    end = regular_season_end().get(s, pd.Timestamp(s + 1, 4, 20))
    return s + 1 if d.normalize() > end else s


@lru_cache(maxsize=1)
def regular_season_start() -> dict:
    """{season start year: date of its first regular-season game} from games.csv (2026-10-19)."""
    g = pd.read_csv(SOURCE_DIR / "games.csv", usecols=["season", "game_type", "game_date"])
    g = g[g["game_type"] == 2]
    g["syr"] = g["season"].astype(str).str[:4].astype(int)
    return pd.to_datetime(g["game_date"]).groupby(g["syr"]).min().to_dict()


# The regular season's last scheduled day as published before the season, where it differs from the last game played.
# games.csv records when the games were played; a trade-day valuation may know only the schedule (CLAUDE.md: a valuation
# draws only on information available before its date). Checked 2026-10-19 against the league's announcements:
#   2019-20: scheduled to end April 4, 2020; the season paused March 12 and its regular season never resumed
#   2020-21: the 56-game schedule (December 2020) ended May 8, 2021; postponements moved the last game to May 19
#   2021-22: scheduled to end April 29, 2022 (kept when the January postponements were rescheduled); one later
#            postponement (Seattle at Winnipeg) was played May 1
# Every other season since 2017-18 ended on its scheduled day.
SCHEDULED_END = {2019: pd.Timestamp("2020-04-04"), 2020: pd.Timestamp("2021-05-08"), 2021: pd.Timestamp("2022-04-29")}


def season_left_share(date, valuation_page) -> float:
    """DECIDED (Thomas, 2026-10-19: "Yes, account for in-season trades"; "Days left, value and cap"): the share of the
    valuation season still to come on the trade date, counted in regular-season days (the cap hit is charged by the day,
    and the season's value follows the same share): (last game - trade date + 1) / (last game - first game + 1), the
    trade day counted as left. 1.0 when the page's regular season has not begun on the date (an off-season trade, or a
    post-season trade valued on the next page); 0 never arises, since a trade after the last game moves to the next page.
    The last day is the schedule's as published before the season (SCHEDULED_END; 2026-10-19), not the last game
    played: a trade on 2020-02-24 counts 41 of 186 scheduled days (22.0%), not the 17 of 162 days the March 12 pause left.
    Example: 2018-02-26 in 2017-18 (2017-10-04 to 2018-04-08): 42 of 187 days, 22.5%."""
    d, p = pd.Timestamp(date).normalize(), int(valuation_page)
    first, last = regular_season_start().get(p), SCHEDULED_END.get(p, regular_season_end().get(p))
    if first is None or last is None or d < first:
        return 1.0
    assert d <= last, (date, valuation_page)               # GUARD: page() sends a later trade to the next page
    return ((last - d).days + 1) / ((last - first).days + 1)
