"""
war_rows.py v1.0 (2026-11-24) -- row-level corrections to Bacon's WAR.csv that no name rule can make.

WHY. WAR.csv labels the b.1988 Erik Gustafsson's seasons "Erik Gustafsson 88" for 2010-11 to 2012-13, but leaves his last
NHL season, 2013-14 with Philadelphia (31 GP), under the plain name the b.1992 Erik Gustafsson carries from 2015-16 on
(the b.1992 player was in Sweden in 2013-14). Read by name, that season became the b.1992 player's, at age 21
(STANDING_FLAGS, 2026-07-19; checked 2026-11-24). Thomas, 2026-11-24: "Fix it".

RULE. Each reader of WAR.csv by player name calls relabel() on the frame it read, before anything else: the one row named
here, matched on player, season and team, takes the other player's label. The source file is never written.
GUARD. Each row must be found exactly once (a vendor refresh that moved or fixed it stops the reader, to be looked at).

NOT APPLIED in prospect_values.season_table (read by the back-test, the rights and the 2017 page): its name rule drops
digits, so it reads "Erik Gustafsson 88" and "Erik Gustafsson" as one player in every season; those tables are read only
from each trade's date on, and the b.1988 player is in no trade, so no value reads his seasons there.
NOT APPLIED in the draft pillar (pick_curve.py, draft_pick_linkage.py): the b.1992 player's draft pick (2012 #93) is already
left out of the pick curve (draft_pick_linkage.MERGED_NAME_EXCLUDED_PICKS), so it stays as it is.
"""
import pandas as pd

SCRIPT_VERSION = "war_rows.py v1.0 (2026-11-24)"

# (player as WAR.csv writes him, season as WAR.csv writes it, team) -> the label the row belongs under
ROW_RELABELS = {("Erik Gustafsson", "13-14", "PHI"): "Erik Gustafsson 88"}


def relabel(w: pd.DataFrame, name_col: str = "Player") -> pd.DataFrame:
    """The frame with each listed row moved to its player's label. Needs name_col, Season and Team."""
    missing = {name_col, "Season", "Team"} - set(w.columns)
    assert not missing, f"war_rows.relabel needs {sorted(missing)}"
    w = w.copy()
    for (name, season, team), to in ROW_RELABELS.items():
        m = (w[name_col] == name) & (w["Season"].astype(str) == season) & (w["Team"].astype(str) == team)
        assert int(m.sum()) == 1, f"war_rows: {name} {season} {team} found {int(m.sum())} times in WAR.csv (expected 1)"
        w.loc[m, name_col] = to
    return w
