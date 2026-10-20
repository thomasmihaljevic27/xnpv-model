"""
ltir.py -- long-term injured reserve: who was on it, when, and how much of a season's cap hit it relieves.

DECIDED (Thomas, 2026-10-20; MODEL_DIRECTIVES "LTIR"): "Fetch a real LTIR log" (Spotrac's NHL injured-reserve pages, one
per season 2017-18 to 2025-26, saved by Thomas into SOURCE_DIR/ltir/: the sites with a full log block automated
requests); relief "All of it" (a day on LTIR costs nothing in the model's currency; cash ignored, as everywhere);
"Outcome + known at trade" (every LTIR day in the back-test's outcome; in a trade's forecast, only a player already on
LTIR when traded, his seasons relieved by the chance he does not play).

THE SOURCE. Each page lists the season's injured players, one row each: player, position, team, and a "Reason" cell of
spells, e.g. "Long-Term IR: Upper Body: 11/16/21-4/10/22" or "IR: Face: 3/21/22-4/5/22". Two labels only: "IR" and
"Long-Term IR". A spell's end "TBD" runs to the season's last regular-season game. Repairs, each counted in the log:
an end before its start one year short (Seabrook "10/12/21-4/10/21") gets the year added; a start that cannot be read
("11/30/-1") is the season's first game. The page's season is read from its own dates (the saved titles do not match).

WHICH SPELLS ARE LTIR. Spotrac labels season-long absences that clubs carried on LTIR as plain "IR" (Ellis 2023-24 and
2024-25, Weber from 2021-22, Hossa 2018-19, Clarkson 2017-19), so the label alone misses them. Two readings, the switch
RULE below, the choice Thomas's (asked 2026-10-20):
  "label"  only spells labelled "Long-Term IR";
  "cba"    those, and any "IR" spell meeting the CBA's own LTIR test (Article 50.10(c): out at least 10 NHL games and
           24 days), counted on his team's regular-season schedule. A club below the cap may not have placed such a
           player on LTIR; in the model's currency the relief is there to take.
A spell counts only inside the regular season (the cap is a regular-season accounting).

WHAT THE OTHER SCRIPTS READ
  relief_share(name, season, after=None)   the share of the season's regular-season days (from `after`, a trade date,
                                           when given) that he spent on LTIR: the share of that season's cap hit relieved
  on_ltir_when_traded(name, date)          True when he was on LTIR on the date, or (an off-season date) his last spell
                                           ran to the end of the season before and he played no NHL game after it
Names are matched as pick_curve and prospect_values match them (accents stripped, lower case, letters only), with the
first name's short or long form (Alex / Alexander).

INPUTS: SOURCE_DIR/ltir/*.html (Spotrac, saved by Thomas), SOURCE_DIR/games.csv.
OUTPUTS (when run): OUTPUT_DIR/ltir_spells.csv (one row per spell), ltir_log.txt.
Run from the repo root:  python 20_CODE/ltir.py
"""

import glob
import html
import os
import re
import sys
import unicodedata
from functools import lru_cache
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

SCRIPT_VERSION = "ltir.py v1.0 (2026-10-20)"
load_dotenv()
SOURCE_DIR, OUTPUT_DIR = Path(os.environ["SOURCE_DIR"]), Path(os.environ["OUTPUT_DIR"])
RULE = os.environ.get("XNPV_LTIR_RULE", "cba")       # "cba" or "label": which spells are LTIR (see above)
LTIR_DAYS, LTIR_GAMES = 24, 10                        # CBA 50.10(c): out at least 24 days and 10 NHL games
SHORT_LONG = (("alexander", "alex"), ("nicholas", "nick"), ("michael", "mike"), ("matthew", "matt"),
              ("joshua", "josh"), ("zachary", "zach"), ("christopher", "chris"), ("daniel", "dan"),
              ("anthony", "tony"), ("samuel", "sam"), ("william", "will"), ("jacob", "jake"))
TEAM = {"WAS": "WSH"}                                  # Spotrac's code -> the schedule's
STATUS = re.compile(r"(Long-Term IR|(?<![A-Za-z-])IR):\s")
RANGE = re.compile(r"(\d{1,2}/\d{1,2}/-?\d{1,2})\s*-\s*(TBD|\d{1,2}/\d{1,2}/\d{2})")
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z ]", "", s.lower().replace("-", " ")).strip()


def keys(name):
    """The name's key and its first-name short or long form."""
    n = norm(name)
    out = [n]
    parts = n.split()
    if len(parts) > 1:
        for lng, sh in SHORT_LONG:
            if parts[0] in (lng, sh):
                out.append(" ".join([sh if parts[0] == lng else lng] + parts[1:]))
    return out


@lru_cache(maxsize=1)
def schedule():
    """Regular-season game dates: {season start: (first, last)} and {(team, season start): sorted dates}."""
    g = pd.read_csv(SOURCE_DIR / "games.csv", usecols=["season", "game_type", "game_date", "home_team", "away_team"])
    g = g[g["game_type"] == 2].copy()
    g["syr"] = g["season"].astype(str).str[:4].astype(int)
    g["d"] = pd.to_datetime(g["game_date"])
    window = {y: (x["d"].min(), x["d"].max()) for y, x in g.groupby("syr")}
    team = {}
    for side in ("home_team", "away_team"):
        for (t, y), x in g.groupby([side, "syr"]):
            team.setdefault((t, y), []).extend(x["d"])
    return window, {k: sorted(v) for k, v in team.items()}


def _date(s):
    m, d, y = s.split("/")
    return pd.Timestamp(2000 + int(y), int(m), int(d))


def parse():
    """Every spell on every saved page: one row each, repaired and clipped to the regular season. Returns (spells,
    repairs counter)."""
    window, team_games = schedule()
    rows, repairs = [], {"end before start": 0, "start unreadable": 0, "TBD": 0}
    files = sorted(glob.glob(str(SOURCE_DIR / "ltir" / "*.html")))
    assert len(files) == 9, files                                      # GUARD: one page per season, 2017-18 to 2025-26
    seen = set()
    for f in files:
        s = open(f, encoding="utf-8", errors="ignore").read()
        cells = []
        for r in re.findall(r"<tr[^>]*>(.*?)</tr>", s, re.S):
            c = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x))).strip()
                 for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
            if len(c) == 7 and c[0] != "Rank":
                cells.append(c)
        # the page's season: the start year most of its dates fall in from October on
        starts = [int("20" + y) - (1 if int(m) < 7 else 0)
                  for m, y in re.findall(r"(\d{1,2})/\d{1,2}/(\d{2})", " ".join(c[4] for c in cells))]
        syr = pd.Series(starts).mode().iloc[0]
        assert syr not in seen and 2017 <= syr <= 2025, (f, syr)        # GUARD: nine different seasons
        seen.add(syr)
        first, last = window[syr]
        for c in cells:
            name, pos, team, reason = c[1], c[2], TEAM.get(c[3], c[3]), c[4]
            marks = list(STATUS.finditer(reason))
            for i, mk in enumerate(marks):
                body = reason[mk.end(): marks[i + 1].start() if i + 1 < len(marks) else len(reason)]
                injury = body.split(":")[0].strip()
                for a, b in RANGE.findall(body):
                    try:
                        st = _date(a)
                    except ValueError:
                        st, repairs["start unreadable"] = first, repairs["start unreadable"] + 1
                    if b == "TBD":
                        en, repairs["TBD"] = last, repairs["TBD"] + 1
                    else:
                        en = _date(b)
                        if en < st:
                            en, repairs["end before start"] = en + pd.DateOffset(years=1), repairs["end before start"] + 1
                    st, en = max(st, first), min(en, last)                 # the regular season only
                    if en < st:
                        continue
                    tg = team_games.get((team, syr), [])
                    games = sum(1 for d in tg if st <= d <= en)
                    rows.append({"season": syr, "player": name, "key": norm(name), "pos": pos, "team": team,
                                 "label": mk.group(1), "injury": injury, "start": st.date(), "end": en.date(),
                                 "days": (en - st).days + 1, "team_games": games,
                                 "cba_test": (en - st).days + 1 >= LTIR_DAYS and games >= LTIR_GAMES})
    d = pd.DataFrame(rows)
    d["ltir"] = (d["label"] == "Long-Term IR") | (d["cba_test"] if RULE == "cba" else False)
    return d, repairs


@lru_cache(maxsize=1)
def spells():
    """The LTIR spells under RULE, by name key: {key: DataFrame}."""
    d, _ = parse()
    d = d[d["ltir"]].copy()
    d["start"], d["end"] = pd.to_datetime(d["start"]), pd.to_datetime(d["end"])
    return {k: g for k, g in d.groupby("key")}


def _mine(name):
    sp = spells()
    for k in keys(name):
        if k in sp:
            return sp[k]
    return None


def relief_share(name, season, after=None):
    """The share of season `season`'s regular-season days (those after the date `after`, when given) he spent on LTIR."""
    window, _ = schedule()
    if season not in window:
        return 0.0
    first, last = window[season]
    if after is not None:
        first = max(first, pd.Timestamp(after) + pd.Timedelta(days=1))
    if last < first:
        return 0.0
    g = _mine(name)
    if g is None:
        return 0.0
    days = set()
    for r in g[g["season"] == season].itertuples():
        a, b = max(r.start, first), min(r.end, last)
        if a <= b:
            days.update(pd.date_range(a, b))                         # overlapping spells counted once
    return len(days) / ((last - first).days + 1)


def on_ltir_when_traded(name, date, games_after=None):
    """On LTIR on `date`: inside a spell, or (off-season) his last spell ran to the season's last game and he played
    no NHL game after it (`games_after(spell_end, date)` -> count, from the caller's game logs)."""
    g = _mine(name)
    if g is None:
        return False
    date = pd.Timestamp(date)
    if ((g["start"] <= date) & (g["end"] >= date)).any():
        return True
    window, _ = schedule()
    before = g[g["end"] < date]
    if before.empty:
        return False
    r = before.sort_values("end").iloc[-1]
    # ran to the season's end: fewer than the CBA's 10 games of his team's season were left after it (Spotrac's end
    # dates can stop a game or two short: Seabrook's 2020-21 spell ends May 8, Chicago played on May 10)
    _, team_games = schedule()
    tg = team_games.get((r["team"], int(r["season"])), [])
    ran_to_end = sum(1 for d in tg if d > r["end"]) < LTIR_GAMES
    if not ran_to_end:
        return False
    nxt = window.get(int(r["season"]) + 1)
    if nxt is not None and date >= nxt[0]:
        return False                                                  # a later season had begun: he was not out then
    return games_after is None or games_after(r["end"], date) == 0


def games_between(nhl_id, a, b):
    """His regular-season and playoff NHL games after date a and before date b (the game logs)."""
    if nhl_id is None or pd.isna(nhl_id):
        return 0
    import sqlite3
    con = sqlite3.connect(SOURCE_DIR / "nhl_gamelogs.sqlite")
    n = 0
    for t in ("skater_games", "goalie_games"):
        n += con.execute(f"select count(*) from {t} s join games g using(game_id) where s.player_id = ? and "
                         f"g.game_date > ? and g.game_date < ?",
                         (int(nhl_id), str(pd.Timestamp(a).date()), str(pd.Timestamp(b).date()))).fetchone()[0]
    return n


def known_on_ltir(names, date, nhl_id=None):
    """on_ltir_when_traded under any of his spellings (the ledger's, the spine's); games after a spell from his NHL id."""
    for nm in names:
        if nm is not None and not (isinstance(nm, float) and pd.isna(nm)) and \
                on_ltir_when_traded(nm, date, lambda a, b: games_between(nhl_id, a, b)):
            return True
    return False


def relief_any(names, season, after=None):
    """relief_share under the first of his spellings the log knows."""
    for nm in names:
        if nm is not None and not (isinstance(nm, float) and pd.isna(nm)) and _mine(nm) is not None:
            return relief_share(nm, season, after)
    return 0.0


def forecast_relief(detail):
    """The known-at-trade relief of an engine valuation (NPVEngine.npv's detail, its own dollars): each contract
    season's carried cap hit, prorated and discounted as the engine does, times the chance he does not play."""
    c = detail[detail["row_type"] == "contract"]
    return float((c["cost_carried"] * c["season_share"] * c["discount"] * (1 - c["survival"])).sum())


def main():
    sys.stdout.reconfigure(errors="replace")
    log(SCRIPT_VERSION)
    log(f"  rule: {RULE} (XNPV_LTIR_RULE); the CBA test: {LTIR_DAYS}+ days and {LTIR_GAMES}+ team games")
    d, repairs = parse()
    log(f"  spells read: {len(d):,} on {d['season'].nunique()} pages; repairs: {repairs}")
    t = d.groupby("season").agg(spells=("player", "size"), labelled=("label", lambda s: (s == "Long-Term IR").sum()),
                                cba_test=("cba_test", "sum"), ltir=("ltir", "sum"))
    log("  by season (spells; labelled Long-Term IR; meeting the CBA test; counted as LTIR under the rule):")
    log(t.to_string())
    k = d[(d["label"] == "Long-Term IR") & ~d["cba_test"]]
    log(f"  labelled LTIR but short of the CBA test (kept: the label is the club's own filing): {len(k)}")
    for nm in ("Ryan Ellis", "Brent Seabrook", "Nikita Kucherov", "Marian Hossa", "Shea Weber", "Carey Price",
               "David Clarkson", "Bryan Little"):
        log(f"  {nm}: " + ", ".join(f"{y}-{str(y + 1)[2:]} {relief_share(nm, y):.0%}" for y in range(2017, 2026)
                                    if relief_share(nm, y) > 0))
    d.to_csv(OUTPUT_DIR / "ltir_spells.csv", index=False)
    (OUTPUT_DIR / "ltir_log.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
    log(f"wrote ltir_spells.csv and ltir_log.txt in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
