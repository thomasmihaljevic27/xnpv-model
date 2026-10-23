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
rights_values.py (season_left_share, 2026-10-19; retention, 2026-10-20)
and trade_asset_values.py (which also gives each traded pick its page; no pick value depends on it, and
traded_pick_values.py does not record it: corrected 2026-10-18). Import and call page(date).
"""

import os
import re
import sqlite3
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


# The ledger's text for a retained asset: "Jason Demers ($562,500 retained - 12.5%) · $3,937,500 ..."
RETENTION_FROM = "2017-07-01"
RETAINED_TEXT = re.compile(r"\(\$([\d,]+) retained - ([\d.]+)%\)")


@lru_cache(maxsize=1)
def retention() -> pd.DataFrame:
    """DECIDED (Thomas, 2026-10-20: "Charge the 15 retentions recorded only in the trade ledger's text"): every traded
    asset whose cap hit the trading club partly kept, indexed by asset_id:
      retained_aav   the dollars a season the trading club kept
      retention_pct  that as a share of the full cap hit (kept + carried)
      source         "fields" (trades.db's retention_pct and retained_aav) or "ledger text"
    The ledger's parser filled the two fields only where the text's share is a whole number (72 assets); the 15 whose
    share has a decimal (Jason Demers, "$562,500 retained - 12.5%") were left with the amount in the row text alone.
    Those are read from the text: the amount as written, the share as amount / (amount + the acquirer's cap hit,
    cap_hit_aav), which is the full cap hit's share.
    GUARDS: where the fields are set, the text gives the same amount (to $1) and share (to the text's rounding);
    for a text-only asset, the computed share rounds to the text's share (to 0.05 points); every asset whose text
    mentions a retention is in the table. Trades from RETENTION_FROM (2017-07-01, the first the model values): before it
    the ledger's cap hit is not always the acquirer's share (Jordan Leopold, 2014: $500,000 kept of $2,250,000 is
    written as 22.2%), so the share cannot be checked there."""
    con = sqlite3.connect(SOURCE_DIR / "trades.db")
    a = pd.read_sql("select a.asset_id, a.cap_hit_aav, a.retention_pct, a.retained_aav, a.raw_text from trade_assets a "
                    "join trades t using(trade_id) where t.trade_date >= ?", con, params=(RETENTION_FROM,))
    m = a["raw_text"].fillna("").str.extract(RETAINED_TEXT)
    a["text_amt"] = pd.to_numeric(m[0].str.replace(",", ""), errors="coerce")
    a["text_pct"] = pd.to_numeric(m[1], errors="coerce")
    fields = a["retained_aav"].fillna(0) > 0
    text = a["text_amt"].notna()
    mentions = a["raw_text"].fillna("").str.contains("retained", case=False)
    assert (mentions == (fields | text)).all(), "a ledger row mentions a retention that neither the fields nor the text give"
    f = a[fields & text]
    assert ((f["text_amt"] - f["retained_aav"]).abs() <= 1).all(), "fields and text disagree on a retained amount"
    assert ((f["text_pct"] - 100 * f["retention_pct"]).abs() <= 0.5 + 1e-9).all(), "fields and text disagree on a share"
    t = a[text & ~fields].copy()
    t["retained_aav"] = t["text_amt"]
    t["retention_pct"] = t["text_amt"] / (t["text_amt"] + t["cap_hit_aav"])
    assert ((100 * t["retention_pct"] - t["text_pct"]).abs() <= 0.05 + 1e-9).all(), "a text share does not match its amounts"
    out = pd.concat([a[fields].assign(source="fields"), t.assign(source="ledger text")])
    return out.set_index("asset_id")[["retained_aav", "retention_pct", "source"]].astype(
        {"retained_aav": float, "retention_pct": float})
