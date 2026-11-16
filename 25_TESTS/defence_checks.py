"""
defence_checks.py - is the defenceman result the measures' weakness on defence? (Thomas, 2026-11-15: "Yes, run them";
declared in 40_DOCS/Backtest_Protocol.md before it was built. Report only.)

THE FINDING UNDER TEST. Clubs acquiring a defenceman come out worse than even their price predicts (joint regression with
the price held: -$0.67M a side on Bacon's WAR, -$0.93M on Game Value, declared window). Both measures are built from
shot-and-shift data, which captures defence poorly. Is the model overvaluing defencemen, or are the measures
undervaluing them?

THE CHECKS
  0  the loose end: per asset, traded defencemen delivered about their forecast (test B), yet the club sides fall short.
     For club sides whose main player is a defenceman (a forward beside), the side's outcome minus its priced net is
     split into the main player's own miss, the other assets the club received, and the assets it gave.
  1  games against quality per game. Every skater the forecast covers, at every July 1 page 2018-2025, seasons one to
     three ahead (h = 0, 1, 2) through 2025-26. With E = chance of playing x forecast games share, G = the games share he
     delivered (zero if he did not play), r_f = the forecast rate per 82 and r_d = the rate he delivered:
        delivered WAR - expected WAR = G x r_d - E x r_f = (G - E) x r_f   [the games part]
                                                         + G x (r_d - r_f) [the per-game part]
     exactly. Defencemen against forwards; traded in the twelve months after the page against not.
  2  ice time per game in those seasons against his own 50/30/20 trailing ice time per game before the page (seasons of
     10+ games, rescaled over the seasons he has): ice time is the coaches' choice and uses no WAR model
  3  Bacon's WAR by part: the same seasons' per-82 rates of each component against his own 50/30/20 trailing rate
  Dollars: a WAR at the price line's slope (forwards 0.0175093, defencemen 0.0215858 of a cap) at the 2025-26 cap.
  Intervals: 2,000 resamples of players, seed 20261115.

BAKED-IN ASSUMPTIONS
  - position: the player's position in his most recent season before the page (player_season_table `pos`)
  - traded: his name (letters only, first two and last six) in the ledger carried to 2026, July 1 of the page to the next
  - the forecast is the saved one (30_OUTPUT/xnpv1_forecasts.csv, skater_forecast v2.4); rate_82 and gp_share are its
    own parts (war_if_plays = rate_82 x gp_share, asserted)

INPUTS: OUTPUT_DIR/xnpv1_forecasts.csv, trades_extended.db; the extended run's backtest_cuts_all_sides.csv,
        backtest_assets.csv, backtest_assets_gv_adj.csv; player_season_table.build
OUTPUTS: OUTPUT_DIR/defence_checks_log.txt, defence_checks.csv
"""
import os
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
load_dotenv()
import forecast_config as C                          # noqa: E402
import player_season_table as PST                    # noqa: E402
import skater_forward_projection as SFP              # noqa: E402

OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
EXT = OUTPUT_DIR / "_extended_run"
SCRIPT_VERSION = "defence_checks.py v1.1 (2026-11-15)"   # v1.1: part 0 exact (a given asset carries its retained part, as trade_sides)
N_BOOT, SEED = 2000, 20261115
CAP_NOW = SFP.CAP_CEILING[2025]
DECLARED_END = "2022-03-28"
COMP = ["EVO WAR_82", "EVD WAR_82", "PP WAR_82", "PK WAR_82", "Pens WAR_82", "Shoot WAR_82"]
COMP_NAME = {"EVO WAR_82": "even-strength offence", "EVD WAR_82": "even-strength defence", "PP WAR_82": "power play",
             "PK WAR_82": "penalty kill", "Pens WAR_82": "penalties", "Shoot WAR_82": "shooting"}
LOG, OUT = [], []


def log(s=""):
    print(s)
    LOG.append(s)


def key(s):
    x = re.sub("[^a-z]", "", unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower())
    return x[:2] + x[-6:]


def bm(v, g, rng):
    d = pd.DataFrame({"v": np.asarray(v, float), "g": np.asarray(g)}).dropna()
    if d["g"].nunique() < 2:
        return (float(d["v"].mean()) if len(d) else np.nan), np.nan, np.nan
    s, c = d.groupby("g")["v"].sum().values, d.groupby("g")["v"].size().values
    i = rng.integers(0, len(s), (N_BOOT, len(s)))
    b = s[i].sum(1) / c[i].sum(1)
    return float(s.sum() / c.sum()), *np.percentile(b, [2.5, 97.5])


def f3(x, w=6):
    return f"{x[0]:+.{2 if abs(x[0]) >= 0.1 or True else 3}f} [{x[1]:+.2f},{x[2]:+.2f}]" if np.isfinite(x[1]) else f"{x[0]:+.2f}"


def trailing(s, page, col, gp_min=10):
    """50/30/20 over the three seasons before the page, seasons of gp_min+ games, rescaled over the seasons he has."""
    got = [(w, float(s.loc[z, col])) for w, z in zip((0.5, 0.3, 0.2), (page - 1, page - 2, page - 3))
           if z in s.index and s.loc[z, "GP"] >= gp_min and pd.notna(s.loc[z, col])]
    return sum(w * x for w, x in got) / sum(w for w, _ in got) if got else np.nan


def part0(rng):
    log("\n0. THE LOOSE END: club sides by main player, outcome minus priced net split by asset ($M a side, WAR; all trades and declared window)")
    s = pd.read_csv(EXT / "backtest_cuts_all_sides.csv")
    a = pd.read_csv(EXT / "backtest_assets.csv")
    a["miss"] = a["outcome_M"] - a["value_2025_cap_M"]
    con = sqlite3.connect(EXT / "trades_extended.db")
    legs = pd.read_sql("select trade_id, acquiring_team from trade_legs", con)
    clubs = legs.groupby("trade_id")["acquiring_team"].apply(lambda x: sorted(set(x))).to_dict()
    a["sender"] = [r.from_team if pd.notna(r.from_team) else next((c for c in clubs[r.trade_id] if c != r.acquiring_team), None)
                   for r in a.itertuples()]
    ret = a[a["asset_type"] == "retained salary"]
    mv = a[a["asset_type"] != "retained salary"]
    rows = []
    for r in s.itertuples():
        got = mv[(mv["trade_id"] == r.trade_id) & (mv["acquiring_team"] == r.club)]
        gave = mv[(mv["trade_id"] == r.trade_id) & (mv["sender"] == r.club)]
        main = got[got["name"] == r.name] if pd.notna(r.name) else got.iloc[0:0]
        mmiss = float(main["miss"].sum()) if len(main) else 0.0
        rows.append({"trade_id": r.trade_id, "club": r.club, "pos": r.pos, "date": r.trade_date,
                     "side_miss": r.out_net_M - r.net_M, "main_miss": mmiss,
                     "other_recv_miss": float(got["miss"].sum()) - mmiss,
                     # what the sender held = the acquirer's value plus the retained part (trade_sides.club_sides' rule)
                     "gave_miss": -float(gave["miss"].sum() + ret[ret["asset_id"].isin(gave["asset_id"])]["miss"].sum()),
                     "retained_miss": float(ret[(ret["trade_id"] == r.trade_id) & (ret["acquiring_team"] == r.club)]["miss"].sum())})
    d = pd.DataFrame(rows)
    d["rest"] = d["side_miss"] - d["main_miss"] - d["other_recv_miss"] - d["gave_miss"] - d["retained_miss"]
    log(f"  check: the parts add up to the side's miss to within ${d['rest'].abs().max():.6f}M")
    assert d["rest"].abs().max() < 1e-6                                              # GUARD: the split is exact
    log(f"  {'main player':<14}{'scope':<18}{'sides':>6}{'side: outcome - priced':>26}{'main player':>24}{'other received':>24}{'given (sign flipped)':>24}{'retained':>10}")
    for pos in ("D", "F"):
        for sc, m in (("all trades", pd.Series(True, index=d.index)), ("declared window", d["date"] <= DECLARED_END)):
            g = d[m & (d["pos"] == pos)]
            cells = [f3(bm(g[c], g["trade_id"], rng)) for c in ("side_miss", "main_miss", "other_recv_miss", "gave_miss")]
            log(f"  {pos:<14}{sc:<18}{len(g):>6}" + "".join(f"{c:>24}" for c in cells[:1]) + "  " + "".join(f"{c:>24}" for c in cells[1:])
                + f"{g['retained_miss'].mean():>+10.2f}")
            for c in ("side_miss", "main_miss", "other_recv_miss", "gave_miss"):
                e = bm(g[c], g["trade_id"], rng)
                OUT.append({"part": "0", "group": f"main {pos}, {sc}", "measure": c, "n": len(g), "mean": e[0], "lo": e[1], "hi": e[2]})


def main():
    rng = np.random.default_rng(SEED)
    log(SCRIPT_VERSION)
    log(f"  reads {OUTPUT_DIR} and {EXT}")
    part0(rng)

    bd, _ = PST.birthdate_source()
    T = PST.build(birthdate_csv=bd, verbose=False)
    T = T.groupby(["career_key", "syr"], as_index=False).agg(
        GP=("GP", "sum"), WAR=("WAR", "sum"), TOI=("TOI", "sum"), gp_share=("gp_share", "sum"), pos=("pos", "last"),
        **{c: (c, "mean") for c in ["WAR_82"] + COMP})                               # a traded season: one row (rates averaged; rare)
    T["toi_pg"] = T["TOI"] / T["GP"]
    by = {k: g.set_index("syr") for k, g in T.groupby("career_key")}
    fc = pd.read_csv(OUTPUT_DIR / "xnpv1_forecasts.csv", usecols=["career_key", "page", "h", "rate_82", "gp_share", "p_play", "war_if_plays"])
    assert np.allclose(fc["war_if_plays"], fc["rate_82"] * fc["gp_share"], atol=1e-9)   # GUARD: the forecast's identity
    fc = fc[(fc["h"] <= 2) & (fc["page"] + fc["h"] <= C.LAST_SOURCE_SEASON)]
    con = sqlite3.connect(OUTPUT_DIR / "trades_extended.db")
    ta = pd.read_sql("select a.player_name, t.trade_date from trade_assets a join trades t using(trade_id) where a.asset_type = 'player'", con)
    ta["k"], ta["d"] = ta["player_name"].map(key), pd.to_datetime(ta["trade_date"])
    tk = {k: g["d"].values for k, g in ta.groupby("k")}

    def traded(ck, page):
        x = tk.get(key(ck))
        return False if x is None else bool(((x >= np.datetime64(f"{page}-07-01")) & (x < np.datetime64(f"{page + 1}-07-01"))).any())
    rows = []
    for r in fc.itertuples():
        s = by.get(r.career_key)
        if s is None:
            continue
        prior = s[s.index < r.page]
        if prior.empty:
            continue
        pos = prior["pos"].iloc[-1]
        y = r.page + r.h
        played = y in s.index
        G = float(s.loc[y, "gp_share"]) if played else 0.0
        rd = float(s.loc[y, "WAR_82"]) if played else np.nan
        E = r.p_play * r.gp_share
        row = {"ck": r.career_key, "page": r.page, "h": r.h, "pos": pos, "traded": traded(r.career_key, r.page),
               "expected": E * r.rate_82, "delivered": G * (rd if played else 0.0),
               "games_part": (G - E) * r.rate_82, "pergame_part": G * (rd - r.rate_82) if played else 0.0,
               "toi_d": float(s.loc[y, "toi_pg"]) if played else np.nan, "toi_t": trailing(s, r.page, "toi_pg")}
        for c in COMP:
            row[c + "_d"] = float(s.loc[y, c]) if played and s.loc[y, "GP"] >= 10 else np.nan
            row[c + "_t"] = trailing(s, r.page, c)
        rows.append(row)
    d = pd.DataFrame(rows)
    d["miss"] = d["delivered"] - d["expected"]
    assert np.allclose(d["miss"], d["games_part"] + d["pergame_part"], atol=1e-9)        # GUARD: the split is exact
    d["slope"] = np.where(d["pos"] == "D", SFP.price_constants()[2], SFP.price_constants()[1]) * CAP_NOW / 1e6
    d.to_csv(OUTPUT_DIR / "defence_checks_rows.csv", index=False)
    log(f"\n  forecast-seasons scored (pages 2018-2025, one to three seasons ahead, through 2025-26): {len(d):,}; players {d['ck'].nunique():,}; "
        f"traded within twelve months of the page {int(d['traded'].sum()):,}")

    # ---- 1 ---------------------------------------------------------------------------------------------------------------
    log("\n1. GAMES AGAINST QUALITY PER GAME (WAR a season; $M in brackets at the price line's slope)")
    log(f"  {'group':<34}{'seasons':>8}{'players':>8}{'delivered - expected':>28}{'games part':>28}{'per-game part':>28}")
    for pos in ("D", "F"):
        for lab, m in (("traded", d["traded"]), ("not traded", ~d["traded"])):
            g = d[(d["pos"] == pos) & m]
            cells = []
            for c in ("miss", "games_part", "pergame_part"):
                e = bm(g[c], g["ck"], rng)
                cells.append(f"{f3(e)} (${e[0] * g['slope'].mean():+.2f}M)")
                OUT.append({"part": "1", "group": f"{pos}, {lab}", "measure": c, "n": len(g), "mean": e[0], "lo": e[1], "hi": e[2]})
            log(f"  {pos + ', ' + lab:<34}{len(g):>8}{g['ck'].nunique():>8}" + "".join(f"{c:>28}" for c in cells))

    # ---- 2 ---------------------------------------------------------------------------------------------------------------
    log("\n2. ICE TIME PER GAME, delivered minus his own 50/30/20 trailing ice time (minutes; seasons he played)")
    d["toi_change"] = d["toi_d"] - d["toi_t"]
    for pos in ("D", "F"):
        cells = {}
        for lab, m in (("traded", d["traded"]), ("not traded", ~d["traded"])):
            g = d[(d["pos"] == pos) & m & d["toi_change"].notna()]
            cells[lab] = (bm(g["toi_change"], g["ck"], rng), len(g))
            OUT.append({"part": "2", "group": f"{pos}, {lab}", "measure": "toi_change", "n": len(g), "mean": cells[lab][0][0],
                        "lo": cells[lab][0][1], "hi": cells[lab][0][2]})
        log(f"  {pos}: traded {f3(cells['traded'][0])} (n={cells['traded'][1]}); not traded {f3(cells['not traded'][0])} (n={cells['not traded'][1]}); "
            f"gap {cells['traded'][0][0] - cells['not traded'][0][0]:+.2f} minutes")

    # ---- 3 ---------------------------------------------------------------------------------------------------------------
    log("\n3. BACON'S WAR BY PART: per-82 rate delivered minus his own 50/30/20 trailing rate (seasons of 10+ games), traded minus not traded")
    log(f"  {'part':<24}" + "".join(f"{p + ' traded':>22}{p + ' not traded':>22}{p + ' gap':>12}" for p in ("D", "F")))
    for c in COMP:
        d[c + "_chg"] = d[c + "_d"] - d[c + "_t"]
        cells = []
        for pos in ("D", "F"):
            tr = d[(d["pos"] == pos) & d["traded"] & d[c + "_chg"].notna()]
            nt = d[(d["pos"] == pos) & ~d["traded"] & d[c + "_chg"].notna()]
            a, b = bm(tr[c + "_chg"], tr["ck"], rng), bm(nt[c + "_chg"], nt["ck"], rng)
            cells += [f3(a), f3(b), f"{a[0] - b[0]:+.3f}"]
            OUT.append({"part": "3", "group": f"{pos}, {COMP_NAME[c]}", "measure": "traded_minus_not", "n": len(tr), "mean": a[0] - b[0],
                        "traded": a[0], "traded_lo": a[1], "traded_hi": a[2], "not_traded": b[0]})
        log(f"  {COMP_NAME[c]:<24}" + "".join(f"{x:>22}" if i % 3 != 2 else f"{x:>12}" for i, x in enumerate(cells)))
    pd.DataFrame(OUT).to_csv(OUTPUT_DIR / "defence_checks.csv", index=False)
    (OUTPUT_DIR / "defence_checks_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
