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

Used by prospect_values.py, traded_player_values.py, page_2017_values.py, contracts_2017.py, buried_contract_values.py
and traded_pick_values.py (picks: recorded, no value depends on the page). Import and call page(date).
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
