"""
backtest_cuts_more.py - four more exploratory cuts (40_DOCS/Backtest_Protocol.md, "Four more exploratory cuts",
declared 2026-11-12 before any was computed; Thomas: "continue with 5a, 8, 16, and GM tenure").

  5a  former top-15 picks who have not broken out, at every July 1 page, traded or not: are they held too long?
  8   cap pressure: (i) paying to move a contract, by the trade's structure; (ii) club payroll on the trade date
  16  offer sheets: a what-if on every contract a restricted free agent signed from 2018 on
  GM  a new general manager's first year: does he sell his predecessor's players cheaply?

It reads the extended run as written and re-values nothing. Run with OUTPUT_DIR on 30_OUTPUT/_extended_run.
Money is $M at the 2025-26 cap unless a line says otherwise. Intervals: 2,000 resamples of trades (cuts 8 and GM) or of
players (5a) or contracts (16), seed 20261112.

BAKED-IN ASSUMPTIONS (the protocol's declared rules; each is repeated where it is applied)
  - the benchmark for "broken out" is backtest_cuts.py's: the mean season WAR of top-15 skaters of the 2005-2012 drafts
    in D+5 and later through 2016-17, and the trailing total is the forecast's 50/30/20 over seasons of 10+ games
    (backtest.trailing_total's rule, re-implemented here on WAR_with_age.csv)
  - a panel value is stated at the 2025-26 cap by the ratio of ceilings, as trade_asset_values.py
  - payroll is an estimate (see cut 8); the offer-sheet thresholds are the printed ones for every year (OFFER_BOUNDS)
  - the general managers' dates are Wikipedia's club lists, read 2026-11-12 (GM_TENURES)

INPUTS: OUTPUT_DIR/backtest_sides.csv, backtest_sides_gv_adj.csv, backtest_assets.csv, prospect_values.csv,
        contract_npv_panel.csv, contract_level_spine.csv, contract_season_spine.csv, pick_curve_players.csv,
        pick_curve_later_players.csv, pick_curve_seasons.csv, pick_curve_scales.csv, WAR_with_age.csv, trades_extended.db;
        SOURCE_DIR/nhl_gamelogs.sqlite, games.csv, draft_slot_baseline.csv; the PuckPedia contract export
OUTPUTS: OUTPUT_DIR/backtest_cuts_more.csv, backtest_cuts_more_log.txt
"""
import os
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
load_dotenv()
import backtest_cuts as BC                           # noqa: E402  the tables and the resampling
import contract_source as CS                         # noqa: E402
import skater_forward_projection as SFP              # noqa: E402  the cap ceilings

SOURCE_DIR, OUTPUT_DIR = Path(os.environ["SOURCE_DIR"]), Path(os.environ["OUTPUT_DIR"])
SCRIPT_VERSION = "backtest_cuts_more.py v1.2 (2026-11-12)"   # v1.2: the offer-sheet thresholds as printed (Thomas's table), every year; v1.1: the tier bound's rounding; the tendered sheet matched on AAV (two Sebastian Ahos)
N_BOOT, SEED = 2000, 20261112
CAP = SFP.CAP_CEILING
CAP_NOW = CAP[2025]
DECLARED_END = "2022-03-28"
log = BC.log

# ---- offer-sheet compensation (cut 16) ---------------------------------------------------------------------------------
# The upper bound of each compensation tier, by offseason, as printed in the table Thomas supplied on 2026-11-12 (its
# sources: Pro Hockey Rumors 2018 and 2020, Colligan Hockey 2019, Sportsnet 2021; 2022-2025 from the same table). v1.0-v1.1
# built these from the 2005 brackets times a yearly factor recalled by Claude; every printed figure equals that build to
# within $3, so no contract changes tier except by the $10 of slack v1.1 needed and v1.2 drops.
OFFER_BOUNDS = {
    2018: [1_339_575, 2_029_659, 4_059_322, 6_088_980, 8_118_641, 10_148_302],
    2019: [1_395_053, 2_113_716, 4_227_437, 6_341_152, 8_454_871, 10_568_589],
    2020: [1_439_820, 2_181_545, 4_363_095, 6_544_640, 8_726_188, 10_907_735],
    2021: [1_356_540, 2_055_364, 4_110_732, 6_166_096, 8_221_463, 10_276_829],
    2022: [1_386_490, 2_100_742, 4_201_488, 6_302_230, 8_402_975, 10_503_720],
    2023: [1_415_740, 2_145_061, 4_290_125, 6_435_186, 8_580_250, 10_725_314],
    2024: [1_511_701, 2_290_457, 4_580_917, 6_871_374, 9_161_834, 11_452_294],
    2025: [1_544_424, 2_340_037, 4_680_076, 7_020_113, 9_360_153, 11_700_192],
}
OFFER_TIERS = ["none", "3rd", "2nd", "1st and 3rd", "1st, 2nd and 3rd", "two 1sts, 2nd and 3rd", "four 1sts"]
OFFER_PICKS = [[], [3], [2], [1, 3], [1, 2, 3], [1, 1, 2, 3], [1, 1, 1, 1]]          # rounds owed
TENDERED = [("Sebastian Aho", 2019, 5, 8_454_000, "matched"), ("Jesperi Kotkaniemi", 2021, 1, 6_100_015, "not matched"),
            ("Philip Broberg", 2024, 2, 4_580_917, "not matched"), ("Dylan Holloway", 2024, 2, 2_290_457, "not matched")]

# ---- general managers (cut GM): club, name, start, end; Wikipedia's club lists, read 2026-11-12 -------------------------
GM_TENURES = """ANA|Bob Murray|2008-11-12|2021-11-10
ANA|Jeff Solomon|2021-11-16|2022-02-03
ANA|Pat Verbeek|2022-02-03|
ARI|John Chayka|2016-05-05|2020-07-26
ARI|Steve Sullivan|2020-07-26|2020-09-16
ARI|Bill Armstrong|2020-09-16|2024-04-18
UTA|Bill Armstrong|2020-09-16|
BOS|Don Sweeney|2015-05-20|
BUF|Jason Botterill|2017-05-11|2020-06-16
BUF|Kevyn Adams|2020-06-16|2025-12-15
BUF|Jarmo Kekalainen|2025-12-15|
CGY|Brad Treliving|2014-04-28|2023-04-17
CGY|Don Maloney|2023-04-17|2023-05-23
CGY|Craig Conroy|2023-05-23|
CAR|Ron Francis|2014-04-28|2018-03-07
CAR|Don Waddell|2018-05-08|2024-05-24
CAR|Eric Tulsky|2024-05-24|
CHI|Stan Bowman|2009-07-14|2021-10-26
CHI|Kyle Davidson|2021-10-26|
COL|Joe Sakic|2014-09-19|2022-07-11
COL|Chris MacFarland|2022-07-11|2026-06-02
CBJ|Jarmo Kekalainen|2013-02-13|2024-02-15
CBJ|John Davidson|2024-02-15|2024-05-28
CBJ|Don Waddell|2024-05-28|
DAL|Jim Nill|2013-04-29|
DET|Ken Holland|1997-07-18|2019-04-19
DET|Steve Yzerman|2019-04-19|
EDM|Peter Chiarelli|2015-04-24|2019-01-22
EDM|Keith Gretzky|2019-01-23|2019-05-07
EDM|Ken Holland|2019-05-07|2024-06-27
EDM|Jeff Jackson|2024-06-27|2024-07-24
EDM|Stan Bowman|2024-07-24|
FLA|Dale Tallon|2017-04-10|2020-08-10
FLA|Bill Zito|2020-09-02|
LAK|Rob Blake|2017-04-10|2025-05-05
LAK|Ken Holland|2025-05-14|
MIN|Chuck Fletcher|2009-05-22|2018-04-23
MIN|Paul Fenton|2018-05-21|2019-07-30
MIN|Bill Guerin|2019-08-21|
MTL|Marc Bergevin|2012-05-02|2021-11-28
MTL|Kent Hughes|2022-01-18|
NSH|David Poile|1997-07-09|2023-06-30
NSH|Barry Trotz|2023-07-01|
NJD|Ray Shero|2015-05-04|2020-01-12
NJD|Tom Fitzgerald|2020-01-12|2026-04-06
NJD|Sunny Mehta|2026-04-16|
NYI|Garth Snow|2006-07-18|2018-06-05
NYI|Lou Lamoriello|2018-06-05|2025-04-22
NYI|Mathieu Darche|2025-05-23|
NYR|Jeff Gorton|2015-07-01|2021-05-05
NYR|Chris Drury|2021-05-05|
OTT|Pierre Dorion|2016-04-10|2023-11-01
OTT|Steve Staios|2023-11-01|
PHI|Ron Hextall|2014-05-07|2018-11-26
PHI|Chuck Fletcher|2018-12-03|2023-03-10
PHI|Daniel Briere|2023-03-10|
PIT|Jim Rutherford|2014-06-06|2021-01-27
PIT|Patrik Allvin|2021-01-27|2021-02-09
PIT|Ron Hextall|2021-02-09|2023-04-14
PIT|Kyle Dubas|2023-06-01|
SJS|Doug Wilson|2003-05-13|2022-04-07
SJS|Joe Will|2022-04-07|2022-07-05
SJS|Mike Grier|2022-07-05|
SEA|Ron Francis|2019-07-18|2025-04-22
SEA|Jason Botterill|2025-04-22|
STL|Doug Armstrong|2010-07-01|
TBL|Steve Yzerman|2010-05-25|2018-09-11
TBL|Julien BriseBois|2018-09-11|
TOR|Lou Lamoriello|2015-07-23|2018-04-30
TOR|Kyle Dubas|2018-05-11|2023-05-19
TOR|Brad Treliving|2023-05-31|2026-03-30
VAN|Jim Benning|2014-05-21|2021-12-05
VAN|Stan Smyl|2021-12-05|2021-12-09
VAN|Jim Rutherford|2021-12-09|2022-01-26
VAN|Patrik Allvin|2022-01-26|
VGK|George McPhee|2016-07-13|2019-09-01
VGK|Kelly McCrimmon|2019-09-01|
WSH|Brian MacLellan|2014-05-26|2024-07-08
WSH|Chris Patrick|2024-07-08|
WPG|Kevin Cheveldayoff|2011-06-08|"""
# Notes on the table: Utah carries Bill Armstrong's Arizona start (the same job moved with the franchise, so he is not new
# in 2024). Steve Staios and Kyle Dubas count from their interim start. Tenures ending after 2026-03-13 (the last trade) are
# left open or as printed; it changes nothing here.

ROWS = []


def boot(values, groups, rng):
    """Mean of values resampling `groups` (players or contracts). est, lo, hi."""
    d = pd.DataFrame({"v": np.asarray(values, float), "g": np.asarray(groups)}).dropna()
    if d["g"].nunique() < 2:
        return (float(d["v"].mean()) if len(d) else np.nan), np.nan, np.nan
    s, c = d.groupby("g")["v"].sum().values, d.groupby("g")["v"].size().values
    idx = rng.integers(0, len(s), (N_BOOT, len(s)))
    v = s[idx].sum(1) / c[idx].sum(1)
    return float(s.sum() / c.sum()), *np.percentile(v, [2.5, 97.5])


def f3(x):
    return f"{x[0]:+.2f} [{x[1]:+.2f},{x[2]:+.2f}]" if np.isfinite(x[1]) else f"{x[0]:+.2f}"


def war_table():
    """{nhl_id: DataFrame indexed by season start with GP, WAR}: WAR_with_age.csv, a season's rows (clubs) added up.
    Rows without an NHL id (older seasons) are joined by the spelling the id's own rows carry."""
    w = pd.read_csv(OUTPUT_DIR / "WAR_with_age.csv", usecols=["Player", "Season", "GP", "WAR", "nhl_id"])
    w["y"] = 2000 + w["Season"].str[:2].astype(int)
    names = w.dropna(subset=["nhl_id"]).groupby("nhl_id")["Player"].agg(lambda x: set(x)).to_dict()
    by_name = {n: g for n, g in w.groupby("Player")}
    out = {}
    for nid, ns in names.items():
        g = pd.concat([by_name[n] for n in ns])
        g = g[g["nhl_id"].isna() | (g["nhl_id"] == nid)]
        out[int(nid)] = g.groupby("y")[["GP", "WAR"]].sum()
    return out


def trailing(s, page):
    """The forecast's 50/30/20 trailing WAR total before the page, seasons of 10+ games, rescaled (backtest.trailing_total)."""
    if s is None:
        return np.nan
    got = [(w, float(s.loc[z, "WAR"])) for w, z in zip((0.5, 0.3, 0.2), (page - 1, page - 2, page - 3))
           if z in s.index and s.loc[z, "GP"] >= 10]
    return sum(w * x for w, x in got) / sum(w for w, _ in got) if got else np.nan


def benchmark():
    pcp = pd.read_csv(OUTPUT_DIR / "pick_curve_players.csv")
    pcs = pd.read_csv(OUTPUT_DIR / "pick_curve_seasons.csv")
    top = pcp[(pcp["pick"] <= 15) & pcp["draftYear"].between(2005, 2012) & (pcp["is_goalie"] != True)]   # noqa: E712
    grid = [(r.draftYear, r.pick, y) for r in top.itertuples() for y in range(int(r.draftYear) + 4, min(2016, int(r.window_end) - 1) + 1)]
    w = pcs.set_index(["draftYear", "pick", "season"])["war_82"]
    return float(np.mean([w.get(k, 0.0) for k in grid]))


# ==========================================================================================================================
def cut_5a(rng, W, bench):
    log("\n5a. FORMER TOP-15 PICKS, EVERY JULY 1 PAGE 2018-2025, TRADED OR NOT")
    pk = pd.concat([pd.read_csv(OUTPUT_DIR / f)[["draftYear", "pick", "player", "playerId", "is_goalie"]]
                    for f in ("pick_curve_players.csv", "pick_curve_later_players.csv")])
    pk = pk[(pk["pick"] <= 15) & pk["draftYear"].between(2009, 2020) & (pk["is_goalie"] != True) & pk["playerId"].notna()]   # noqa: E712
    pk = pk.sort_values("draftYear").drop_duplicates("playerId", keep="last")           # drafted twice: the later draft
    sp = pd.read_csv(OUTPUT_DIR / "contract_level_spine.csv", usecols=["player_id", "nhl_id"]).drop_duplicates()
    pan = pd.read_csv(OUTPUT_DIR / "contract_npv_panel.csv", low_memory=False)
    pan = pan[pan["valuation_season"].between(2018, 2025)].merge(sp, on="player_id")
    # one value a player-page: two contracts in a season (38 player-pages) are added up
    v = pan.groupby(["nhl_id", "valuation_season"], as_index=False)["npv_total"].sum()
    v = v.merge(pk.rename(columns={"playerId": "nhl_id"}), on="nhl_id")
    v["n"] = v["valuation_season"] - v["draftYear"] + 1                                  # D+n: the page's season
    v = v[v["n"] >= 5].copy()
    v["value"] = v["npv_total"] * [CAP_NOW / CAP[int(y)] for y in v["valuation_season"]] / 1e6
    v["trail"] = [trailing(W.get(int(i)), int(y)) for i, y in zip(v["nhl_id"], v["valuation_season"])]
    v["below"] = v["trail"] < bench
    # traded in the twelve months from the page's July 1 (the ledger carried to 2026, by spelling)
    con = sqlite3.connect(OUTPUT_DIR / "trades_extended.db")
    ta = pd.read_sql("select a.player_name, t.trade_date from trade_assets a join trades t using(trade_id) where a.asset_type='player'", con)
    ta["k"], ta["d"] = ta["player_name"].map(BC_name), pd.to_datetime(ta["trade_date"])
    tk = {k: g["d"].values for k, g in ta.groupby("k")}
    v["k"] = v["player"].map(BC_name)

    def traded(k, y):
        d = tk.get(k)
        return False if d is None else bool(((d >= np.datetime64(f"{y}-07-01")) & (d < np.datetime64(f"{y + 1}-07-01"))).any())
    v["traded_next"] = [traded(k, int(y)) for k, y in zip(v["k"], v["valuation_season"])]
    v = v.sort_values(["nhl_id", "valuation_season"])
    v["value_next"] = v.groupby("nhl_id")["value"].shift(-1).where(v.groupby("nhl_id")["valuation_season"].shift(-1) == v["valuation_season"] + 1)
    v["later_above"] = [bool((v.loc[(v["nhl_id"] == i) & (v["valuation_season"] > y), "trail"] >= bench).any())
                        for i, y in zip(v["nhl_id"], v["valuation_season"])]
    v["has_later"] = [bool(((v["nhl_id"] == i) & (v["valuation_season"] > y)).any()) for i, y in zip(v["nhl_id"], v["valuation_season"])]
    v.to_csv(OUTPUT_DIR / "backtest_cuts_more_5a_rows.csv", index=False)
    log(f"  benchmark {bench:.3f} WAR; {v['nhl_id'].nunique()} players, {len(v)} player-pages in D+5 or later with a contract the model values; "
        f"no trailing total on {int(v['trail'].isna().sum())} pages (left out of both groups)")
    for lab, g0 in (("BELOW the benchmark", v[v["below"]]), ("AT OR ABOVE the benchmark", v[(v["trail"] >= bench)])):
        log(f"\n  {lab}: {g0['nhl_id'].nunique()} players, {len(g0)} player-pages")
        log(f"  {'season':<9}{'players':>8}{'mean value':>22}{'median':>8}{'traded in 12 months':>21}{'later at/above':>16}"
            f"{'held: value next page minus this':>36}")
        for n in (5, 6, 7, 8, 9, 10):
            g = g0[g0["n"] == n] if n < 10 else g0[g0["n"] >= 10]
            if len(g) == 0:
                continue
            mv = boot(g["value"], g["nhl_id"], rng)
            hl = g[g["has_later"]]
            held = g[~g["traded_next"] & g["value_next"].notna()]
            ch = boot(held["value_next"] - held["value"], held["nhl_id"], rng)
            log(f"  {'D+' + str(n) + ('+' if n == 10 else ''):<9}{len(g):>8}{f3(mv):>22}{g['value'].median():>+8.2f}"
                f"{g['traded_next'].mean():>20.0%} {f'{hl.later_above.mean():.0%} of {len(hl)}' if len(hl) else 'n/a':>15}"
                f"{(f3(ch) + f' (n={len(held)})') if len(held) else 'n/a':>36}")
            ROWS.append({"cut": "5a", "group": f"{lab}, D+{n}", "n": len(g), "value_mean": mv[0], "value_lo": mv[1], "value_hi": mv[2],
                         "value_median": g["value"].median(), "traded_next": g["traded_next"].mean(),
                         "later_above": hl["later_above"].mean() if len(hl) else np.nan, "n_later": len(hl),
                         "held_change": ch[0], "held_change_lo": ch[1], "held_change_hi": ch[2], "n_held": len(held)})
    b = v[v["below"]]
    first = b.sort_values("valuation_season").drop_duplicates("nhl_id")                 # each player's first page below
    fl = first[first["has_later"]]
    log(f"\n  each below-benchmark player once, at his first such page ({len(first)} players): later at or above the benchmark "
        f"{fl['later_above'].mean():.0%} of the {len(fl)} with a later page; traded within twelve months {first['traded_next'].mean():.0%}; "
        f"mean model value {first['value'].mean():+.2f}, median {first['value'].median():+.2f}")
    for lab, g in (("traded within twelve months of a page", b[b["traded_next"]]), ("not traded within twelve months", b[~b["traded_next"]])):
        log(f"  below the benchmark, {lab}: {len(g)} player-pages ({g['nhl_id'].nunique()} players), model value mean "
            f"{f3(boot(g['value'], g['nhl_id'], rng))}, median {g['value'].median():+.2f}")


def BC_name(s):
    """Name key: letters only, first two and last six (as trade_ledger_reconcile.py)."""
    import re
    import unicodedata
    x = re.sub("[^a-z]", "", unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower())
    return x[:2] + x[-6:]


# ==========================================================================================================================
def load_sides():
    s = pd.read_csv(OUTPUT_DIR / "backtest_sides.csv")
    sg = pd.read_csv(OUTPUT_DIR / "backtest_sides_gv_adj.csv")
    assert (s[["trade_id", "club"]].values == sg[["trade_id", "club"]].values).all()
    s["gv_net_M"] = sg["out_net_M"].values
    s = s[s["complete"]].copy()
    s["date"] = pd.to_datetime(s["trade_date"])
    a = pd.read_csv(OUTPUT_DIR / "backtest_assets.csv")
    a = a[a["trade_id"].isin(s["trade_id"])].copy()
    a["date"] = pd.to_datetime(a["trade_date"])
    con = sqlite3.connect(OUTPUT_DIR / "trades_extended.db")
    legs = pd.read_sql("select trade_id, acquiring_team from trade_legs", con)
    clubs = legs.groupby("trade_id")["acquiring_team"].apply(lambda x: sorted(set(x))).to_dict()
    # who sent each asset: from_team in a trade of three or more clubs, else the other club (trade_sides.sender)
    a["sender"] = [r.from_team if pd.notna(r.from_team) else next((c for c in clubs[r.trade_id] if c != r.acquiring_team), None)
                   for r in a.itertuples()]
    pv = pd.read_csv(OUTPUT_DIR / "prospect_values.csv", low_memory=False)[["asset_id", "nhl_id", "cap_hit"]].drop_duplicates("asset_id")
    a = a.merge(pv, on="asset_id", how="left")
    a["is_player"] = (a["asset_type"] == "player") & a["source"].str.startswith(("player model", "buried"))
    a["is_future"] = a["source"].str.startswith(("pick curve", "prospect model"))
    return s, a


def both_scopes(cut, label, g, rng):
    """One group on all trades and on the declared window."""
    BC.side_table(f"{cut} {label}", [("all trades 2017-2026", g), ("declared window (to 2022-03-28)", g[g["trade_date"] <= DECLARED_END]),
                                     ("after 2022-03-28", g[g["trade_date"] > DECLARED_END])], rng)


def cut_8(rng, s, a):
    log("\n8. CAP PRESSURE")
    ss = pd.read_csv(OUTPUT_DIR / "contract_season_spine.csv", low_memory=False,
                     usecols=["nhl_id", "season_start", "pp_signed_end", "pp_signing_date", "model_cap_hit"])
    ss["signed"] = pd.to_datetime(ss["pp_signing_date"])
    by_ps = {k: g for k, g in ss.groupby(["nhl_id", "season_start"])}
    two = s.groupby("trade_id")["club"].transform("size") == 2
    # ---- (i) paying to move a contract ---------------------------------------------------------------------------------
    rows = []
    for tid, g in a[a["trade_id"].isin(s.loc[two, "trade_id"])].groupby("trade_id"):
        for club in g["sender"].dropna().unique():
            sent, got = g[g["sender"] == club], g[g["acquiring_team"] == club]
            big = sent[sent["is_player"] & (sent["cap_hit"] >= 2.5e6)]
            if len(big) == 0 or not sent["is_future"].any() or (got["is_player"] & (got["cap_hit"] >= 1e6)).any():
                continue
            cleared = 0.0
            for r in sent[sent["is_player"]].itertuples():
                page = int(r.valuation_page)
                c = by_ps.get((r.nhl_id, page)) if pd.notna(r.nhl_id) else None
                left = 1
                if c is not None:
                    c = c[c["signed"] <= r.date] if (c["signed"] <= r.date).any() else c
                    left = max(int(c.sort_values("signed").iloc[0]["pp_signed_end"]) - page + 1, 1)
                share = r.season_share if pd.notna(r.season_share) else 1.0
                cleared += r.cap_hit * (share + left - 1) * CAP_NOW / CAP[page] / 1e6
            rows.append({"trade_id": tid, "club": club, "date": g["trade_date"].iloc[0], "player": "; ".join(big["name"]),
                         "cleared_M": cleared, "sweetener_M": sent.loc[sent["is_future"], "value_2025_cap_M"].sum(),
                         "players_value_M": sent.loc[sent["is_player"], "value_2025_cap_M"].sum()})
    d = pd.DataFrame(rows)
    d["price_per_M"] = d["sweetener_M"] / d["cleared_M"]
    d.to_csv(OUTPUT_DIR / "backtest_cuts_more_8_dumps.csv", index=False)
    log(f"  (i) PAYING TO MOVE A CONTRACT (sent a player at $2.5M+ with a pick or prospect; got back no player at $1M+): {len(d)} trades")
    for lab, g in (("all trades 2017-2026", d), ("declared window (to 2022-03-28)", d[d["date"] <= DECLARED_END]), ("after 2022-03-28", d[d["date"] > DECLARED_END])):
        if len(g) == 0:
            continue
        ratio = g["sweetener_M"].sum() / g["cleared_M"].sum()
        ids = g["trade_id"].values
        bs = [g.set_index("trade_id").loc[ids[rng.integers(0, len(ids), len(ids))]].pipe(lambda x: x["sweetener_M"].sum() / x["cleared_M"].sum())
              for _ in range(N_BOOT)]
        log(f"    {lab}: {len(g)} trades; cap cleared mean ${g['cleared_M'].mean():.1f}M (median ${g['cleared_M'].median():.1f}M); picks and prospects sent "
            f"with it mean ${g['sweetener_M'].mean():.2f}M (median ${g['sweetener_M'].median():.2f}M); the models' value of the players sent mean "
            f"${g['players_value_M'].mean():+.2f}M; price of cap space ${ratio:.3f}M of futures per $1M cleared "
            f"[{np.percentile(bs, 2.5):.3f}, {np.percentile(bs, 97.5):.3f}]; per trade median {g['price_per_M'].median():.3f}")
        ROWS.append({"cut": "8i", "group": lab, "n": len(g), "cleared_mean": g["cleared_M"].mean(), "sweetener_mean": g["sweetener_M"].mean(),
                     "price_per_M": ratio, "price_lo": np.percentile(bs, 2.5), "price_hi": np.percentile(bs, 97.5)})
    for r in d.sort_values("cleared_M", ascending=False).head(12).itertuples():
        log(f"      {r.date} {r.club} sent {r.player[:40]:<40} cleared ${r.cleared_M:5.1f}M with futures worth ${r.sweetener_M:5.2f}M")
    recv = s.merge(d[["trade_id", "club"]].rename(columns={"club": "dumper"}), on="trade_id")
    both_scopes("8(i)", "the club that TOOK the contract and the picks or prospects", recv[recv["club"] != recv["dumper"]], rng)

    # ---- (ii) payroll on the trade date --------------------------------------------------------------------------------
    gl = sqlite3.connect(SOURCE_DIR / "nhl_gamelogs.sqlite")
    q = pd.concat([pd.read_sql(f"select s.player_id, s.team, g.game_date from {t} s join games g using(game_id) where g.game_type = 2", gl)
                   for t in ("skater_games", "goalie_games")])
    q["d"] = pd.to_datetime(q["game_date"])
    q = q.sort_values("d")
    first_game = pd.read_csv(SOURCE_DIR / "games.csv", usecols=["season", "game_type", "game_date"])
    first_game = first_game[first_game["game_type"] == 2]
    start = pd.to_datetime(first_game["game_date"]).groupby(first_game["season"].astype(str).str[:4].astype(int)).min().to_dict()
    hit = {(int(n), int(y)): float(h) for n, y, h in ss.groupby(["nhl_id", "season_start"], as_index=False)["model_cap_hit"].max().values}
    cache = {}

    def payroll(date, page):
        if (date, page) not in cache:
            w = q[(q["d"] < date) & (q["d"] >= date - pd.Timedelta(days=365))].drop_duplicates("player_id", keep="last")
            w = w.assign(h=[hit.get((int(p), page), 0.0) for p in w["player_id"]])
            cache[(date, page)] = (w.groupby("team")["h"].sum() / CAP[page]).to_dict()
        return cache[(date, page)]
    m = s[two & s["during_regular_season"]].copy()
    m = m[[d_ >= start.get(int(p), pd.Timestamp("2100-01-01")) + pd.Timedelta(days=20) for d_, p in zip(m["date"], m["valuation_page"])]]
    m["payroll"] = [payroll(d_, int(p)).get(c, np.nan) for d_, p, c in zip(m["date"], m["valuation_page"], m["club"])]
    m = m[m["payroll"].notna()]
    lo, hi = m["payroll"].quantile([1 / 3, 2 / 3])
    log(f"\n  (ii) PAYROLL ESTIMATE on the trade date, in-season two-team trades 20+ days into the season: {len(m)} club sides; payroll as a share "
        f"of the cap: median {m['payroll'].median():.2f}, bottom third below {lo:.2f}, top third above {hi:.2f}")
    BC.side_table("8(ii) club sides by estimated payroll share", [("top third (nearest the ceiling)", m[m["payroll"] > hi]),
                                                                    ("middle third", m[(m["payroll"] <= hi) & (m["payroll"] >= lo)]),
                                                                    ("bottom third", m[m["payroll"] < lo])], rng)
    BC.side_table("8(ii) top third of payroll, by whether the club is higher in the standings",
                  [("top third and higher in the standings", m[(m["payroll"] > hi) & m["g_buyer"]]),
                   ("top third and lower in the standings", m[(m["payroll"] > hi) & ~m["g_buyer"]]),
                   ("other clubs higher in the standings", m[(m["payroll"] <= hi) & m["g_buyer"]])], rng)


# ==========================================================================================================================
def cut_16(rng):
    log("\n16. OFFER SHEETS: A WHAT-IF ON EVERY RFA CONTRACT SIGNED FROM 2018")
    c, _ = CS.load_contracts()
    c = c.drop_duplicates("contract_id").copy()
    c["signed"] = CS.parse_export_dates(c["signing_date"], "PuckPedia signing_date")
    c = c[(c["signing_status"] == "RFA") & (c["contract_level"] == "standard_level") & (c["signed"] >= "2018-06-01")]
    pan = pd.read_csv(OUTPUT_DIR / "contract_npv_panel.csv", low_memory=False)
    pan = pan[pan["seasons_remaining"] == pan["term_years"]]
    first = pan.sort_values("valuation_season").drop_duplicates("contract_id")           # the contract's first page in the panel
    d = c.merge(first[["contract_id", "valuation_season", "npv_total", "term_years", "position"]], on="contract_id")
    d = d[d["term_years"] == d["length"]]                                               # valued whole, from its first season
    d = d[d["valuation_season"].between(2018, 2025)]
    d["year"] = d["valuation_season"].astype(int)                                        # the summer the sheet would be signed
    scales = pd.read_csv(OUTPUT_DIR / "pick_curve_scales.csv").set_index("scale_kind")
    star = float(scales.loc["main", "scale_M"])
    bac = pd.read_csv(SOURCE_DIR / "draft_slot_baseline.csv").set_index("draft_pick")["p_star"]
    rv = {r: star * float(np.mean([bac[s_] for s_ in range((r - 1) * 32 + 1, r * 32 + 1) if s_ in bac.index])) for r in (1, 2, 3)}
    log(f"  compensation picks at the round average (32 clubs; star value ${star:.2f}M): round 1 ${rv[1]:.2f}M, round 2 ${rv[2]:.2f}M, round 3 ${rv[3]:.2f}M")
    log(f"  RFA contracts signed from June 2018 and valued whole from their first season: {len(d)} ({d['player_id'].nunique()} players)")

    def tier(aav, term, y):
        comp = aav * term / min(term, 5)
        return int(sum(comp > b for b in OFFER_BOUNDS[y]))

    def payoff(npv, aav, term, y, prem):
        extra = prem * aav * sum(1 / 1.03 ** k for k in range(int(term)))                 # the extra cap hit, discounted
        t = tier(aav * (1 + prem), int(term), y)
        v = (npv - extra) * CAP_NOW / CAP[y] / 1e6
        return v, sum(rv[r] for r in OFFER_PICKS[t]), t
    out = []
    for r in d.itertuples():
        for prem in (0.0, 0.1, 0.2):
            v, comp, t = payoff(r.npv_total, r.aav, r.term_years, r.year, prem)
            out.append({"contract_id": r.contract_id, "player": f"{r.first_name} {r.last_name}", "year": r.year, "term": r.term_years,
                        "aav": r.aav, "premium": prem, "tier": t, "value_M": v, "comp_M": comp, "payoff_M": v - comp})
    o = pd.DataFrame(out)
    o.to_csv(OUTPUT_DIR / "backtest_cuts_more_16_rows.csv", index=False)
    for prem in (0.0, 0.1, 0.2):
        x = o[o["premium"] == prem]
        log(f"\n  at the signed AAV plus {prem:.0%}: positive payoff for {(x['payoff_M'] > 0).mean():.0%} of {len(x)} contracts")
        log(f"  {'compensation tier':<26}{'contracts':>10}{'picks owed':>12}{'value before picks':>22}{'payoff':>24}{'median':>8}{'payoff > 0':>12}")
        for t in range(7):
            g = x[x["tier"] == t]
            if len(g) == 0:
                continue
            pb, vb = boot(g["payoff_M"], g["contract_id"], rng), boot(g["value_M"], g["contract_id"], rng)
            log(f"  {OFFER_TIERS[t]:<26}{len(g):>10}{g['comp_M'].mean():>11.2f} {f3(vb):>22}{f3(pb):>24}{g['payoff_M'].median():>+8.2f}{(g['payoff_M'] > 0).mean():>11.0%}")
            ROWS.append({"cut": "16", "group": f"premium {prem:.0%}, {OFFER_TIERS[t]}", "n": len(g), "value_mean": vb[0], "payoff_mean": pb[0],
                         "payoff_lo": pb[1], "payoff_hi": pb[2], "payoff_median": g["payoff_M"].median(), "share_positive": (g["payoff_M"] > 0).mean()})
    log("\n  the sheets tendered 2018-2025, at their own terms (value before picks, picks owed, payoff; $M at the 2025-26 cap)")
    for name, y, term, aav, how in TENDERED:
        k = BC_name(name)
        g = d[np.array([BC_name(f"{a_} {b_}") == k for a_, b_ in zip(d["first_name"], d["last_name"])]) & (d["year"] == y).values]
        if len(g) == 0:
            log(f"    {name} {y}: no contract of his valued whole from {y} in the panel")
            continue
        r = g.iloc[(g["aav"] - aav).abs().values.argmin()]                # two Sebastian Ahos signed in 2019: the contract nearest the sheet's AAV
        # the contract in the export is the one he played (the sheet, or the match of it): priced at the sheet's AAV
        v, comp, t = payoff(r.npv_total + (r.aav - aav) * sum(1 / 1.03 ** j for j in range(int(r.term_years))), aav, r.term_years, y, 0.0)
        log(f"    {name} {y} ({how}): {int(r.term_years)} seasons at ${aav:,.0f}; tier {OFFER_TIERS[t]}; value {v:+.2f}, picks {comp:.2f}, payoff {v - comp:+.2f}"
            + ("" if int(r.term_years) == term else f"  [the export's term is {int(r.term_years)}, the sheet's {term}]"))


# ==========================================================================================================================
def cut_gm(rng, s, a):
    log("\nGM TENURE: A NEW GENERAL MANAGER'S FIRST 365 DAYS")
    t = pd.DataFrame([x.split("|") for x in GM_TENURES.splitlines()], columns=["club", "gm", "start", "end"])
    t["start"] = pd.to_datetime(t["start"])
    t["end"] = pd.to_datetime(t["end"].replace("", "2099-01-01"))
    # a person's first day in the job at the club (an interim spell that becomes permanent is one row here already)
    first = t.groupby(["club", "gm"], as_index=False)["start"].min()

    def gm_on(club, d):
        x = t[(t["club"] == club) & (t["start"] <= d) & (t["end"] > d)]
        if len(x) == 0:
            return None, pd.NaT
        g = x.sort_values("start").iloc[-1]["gm"]
        return g, first.loc[(first["club"] == club) & (first["gm"] == g), "start"].iloc[0]
    ss = pd.read_csv(OUTPUT_DIR / "contract_season_spine.csv", low_memory=False, usecols=["nhl_id", "season_start", "pp_signing_date"])
    ss["signed"] = pd.to_datetime(ss["pp_signing_date"])
    by_ps = {k: g for k, g in ss.groupby(["nhl_id", "season_start"])}
    pl = a[a["is_player"]].sort_values("cap_hit", ascending=False, kind="stable").drop_duplicates(["trade_id", "sender"])
    rows = []
    for r in pl.itertuples():
        gm, since = gm_on(r.sender, r.date)
        c = by_ps.get((r.nhl_id, int(r.valuation_page))) if pd.notna(r.nhl_id) else None
        signed = pd.NaT
        if c is not None:
            c = c[c["signed"] <= r.date] if (c["signed"] <= r.date).any() else c
            signed = c.sort_values("signed").iloc[0]["signed"]
        rows.append({"trade_id": r.trade_id, "club": r.sender, "gm": gm, "since": since, "signed": signed, "player": r.name})
    g = s.merge(pd.DataFrame(rows), on=["trade_id", "club"])
    g["days"] = (g["date"] - g["since"]).dt.days
    log(f"  club sides that sent a player: {len(g)}; a general manager on record at the date for {int(g['gm'].notna().sum())}; the player's contract date known "
        f"for {int(g['signed'].notna().sum())}")
    new = g[(g["days"] >= 0) & (g["days"] < 365)]
    newp = new[new["signed"] < new["since"]]
    old = g[g["days"] >= 365]
    log(f"  in a first year: {len(new)} sides by {new.groupby(['club', 'gm']).ngroups} general managers; of them the player's contract predates him: {len(newp)}")
    BC.side_table("GM: the club that SENT its highest-paid player in the trade", [
        ("new GM, predecessor's contract", newp), ("new GM, his own contract or date unknown", new[~(new["signed"] < new["since"])]),
        ("GM past his first year", old),
        ("new GM, predecessor's contract, to 2022-03-28", newp[newp["trade_date"] <= DECLARED_END]),
        ("new GM, predecessor's contract, after", newp[newp["trade_date"] > DECLARED_END]),
        ("GM past his first year, to 2022-03-28", old[old["trade_date"] <= DECLARED_END]),
        ("GM past his first year, after", old[old["trade_date"] > DECLARED_END])], rng)
    BC.side_table("GM: new GM, predecessor's contract, by months in the job", [
        ("first 6 months", newp[newp["days"] < 183]), ("months 7 to 12", newp[newp["days"] >= 183])], rng)
    top = newp.groupby(["club", "gm"]).agg(sides=("trade_id", "size"), priced=("net_M", "mean"), outcome=("out_net_M", "mean")).sort_values("sides", ascending=False)
    log("  the general managers with the most such trades (club sides, mean forecast net, mean outcome):")
    for (club, gm), r in top.head(10).iterrows():
        log(f"    {club} {gm:<20} {int(r.sides):>3}  {r.priced:+.2f}  {r.outcome:+.2f}")


def main():
    rng = np.random.default_rng(SEED)
    log(SCRIPT_VERSION)
    log(f"  reads {OUTPUT_DIR}")
    log(f"  the back-test read: {(OUTPUT_DIR / 'backtest_log.txt').read_text(encoding='utf-8').splitlines()[0]}; "
        f"{[x for x in (OUTPUT_DIR / 'backtest_log.txt').read_text(encoding='utf-8').splitlines() if x.startswith('THE BACK-TEST')][0]}")
    W = war_table()
    bench = benchmark()
    s, a = load_sides()
    cut_5a(rng, W, bench)
    cut_8(rng, s, a)
    cut_16(rng)
    cut_gm(rng, s, a)
    pd.DataFrame(ROWS + BC.ROWS).to_csv(OUTPUT_DIR / "backtest_cuts_more.csv", index=False)
    (OUTPUT_DIR / "backtest_cuts_more_log.txt").write_text("\n".join(BC.LOG), encoding="utf-8")
    log("\nwrote backtest_cuts_more.csv and backtest_cuts_more_log.txt")


if __name__ == "__main__":
    main()
