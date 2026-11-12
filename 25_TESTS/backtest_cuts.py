"""
backtest_cuts.py - the exploratory cuts of the back-test (40_DOCS/Backtest_Protocol.md, "Exploratory cuts",
declared 2026-11-11 before any was computed; Thomas: "Time to look into findings", "Yes, dollar gap").

WHAT IT DOES. Reads the 2026-10-24 back-test's club sides and assets as written (it re-values nothing) and groups
them. For every group it reports, in $M at the 2025-26 cap:
    forecast net  = what the models valued the club's side at on the trade date (received minus given);
                    below zero means the club paid more than the models' value ("priced differently")
    outcome WAR   = the same sum on what each asset delivered, Bacon's WAR ("turned out differently")
    outcome GV    = the same on Game Value adjusted (skaters' realised seasons Bacon-free; goalies keep Bacon)
with the group's club sides, trades, the median and interquartile range of the forecast net, and each mean's 95%
interval from 2,000 resamples of TRADES (a trade's sides move together), seed 20261111.

BAKED-IN ASSUMPTIONS (each is the protocol's declared rule)
  - only complete trades (backtest_sides.complete), as the back-test
  - a side's MAIN PLAYER is the player-model asset it received with the highest ledger cap hit (prospect_values.cap_hit);
    ties go to the first row. Prospects are not players here.
  - age is exact years on the trade date from the contract spine's birthdate (join key nhl_id)
  - contract status, pages 2018 on: the season spine's row for (nhl_id, page) signed on or before the trade date;
    seasons left = pp_signed_end - page + 1. The 2017 page: page_2017_values (contract_last_season, expiry, contract).
  - entry-level is the spine's cs_entry_level (blank on 4,925 spine rows: those fall to the seasons-left groups)
  - clauses: the season spine's has_any_clause at (nhl_id, page), 2018-19 on, as backtest.py's C6
  - the trailing WAR total is backtest_assets.trailing_war (50/30/20, the harness's)

INPUTS: OUTPUT_DIR/backtest_sides.csv, backtest_sides_gv_adj.csv, backtest_assets.csv, backtest_assets_gv_adj.csv,
        prospect_values.csv, traded_player_values.csv, page_2017_values.csv, traded_pick_values.csv,
        contract_season_spine.csv, contract_level_spine.csv, pick_curve_players.csv, pick_curve_seasons.csv
OUTPUTS: OUTPUT_DIR/backtest_cuts.csv, backtest_cuts_log.txt
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
load_dotenv()
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
SCRIPT_VERSION = "backtest_cuts.py v1.2 (2026-11-11)"   # v1.2: the reference check on the back-test after pick_curve v1.12; v1.1: the extended trades (scope), three cap eras, retention by period
# Which trades (protocol, "The extended trades"): "declared" = 2017-07-01 to 2022-03-28 (the default, and the only scope
# the live 30_OUTPUT holds); "new" = after 2022-03-28 (the replication); "all". Set XNPV_CUTS_SCOPE; run with OUTPUT_DIR
# pointing at 30_OUTPUT/_extended_run for "new" and "all".
SCOPE = os.environ.get("XNPV_CUTS_SCOPE", "declared")
assert SCOPE in ("declared", "new", "all")
SUFFIX = "" if SCOPE == "declared" else f"_{SCOPE}"
DECLARED_END = "2022-03-28"
N_BOOT, SEED = 2000, 20261111
DEADLINES = ["2018-02-26", "2019-02-25", "2020-02-24", "2021-04-12", "2022-03-21", "2023-03-03", "2024-03-08", "2025-03-07", "2026-03-06"]
DRAFT_END = {2017: "2017-06-24", 2018: "2018-06-23", 2019: "2019-06-22", 2020: "2020-10-07", 2021: "2021-07-24",
             2022: "2022-07-08", 2023: "2023-06-29", 2024: "2024-06-29", 2025: "2025-06-28",
             2026: "2026-06-30", 2027: "2027-06-30", 2028: "2028-06-30", 2029: "2029-06-30"}   # 2026 on: not yet held, end of June assumed
PAUSE = pd.Timestamp("2020-03-12")
LOG, ROWS = [], []


def log(s=""):
    print(s)
    LOG.append(s)


def boot_mean(g, col, rng):
    """Mean of `col` over the rows of g, resampling trades. Returns est, lo, hi, p (two-sided against zero)."""
    gb = {t: x[col].values for t, x in g.groupby("trade_id")}
    ids = np.array(sorted(gb))
    if len(ids) < 2:
        return float(g[col].mean()) if len(g) else np.nan, np.nan, np.nan, np.nan
    sums = np.array([gb[t].sum() for t in ids])
    cnts = np.array([len(gb[t]) for t in ids])
    idx = rng.integers(0, len(ids), (N_BOOT, len(ids)))
    vals = sums[idx].sum(1) / cnts[idx].sum(1)
    lo, hi = np.percentile(vals, [2.5, 97.5])
    p = min(1.0, 2 * min((vals <= 0).mean(), (vals >= 0).mean()))
    return float(sums.sum() / cnts.sum()), lo, hi, p


def boot_slope(g, ycol, rng):
    """Test A's slope (through zero) of ycol on the forecast net, resampling trades."""
    gb = {t: (float((x["net_M"] * x[ycol]).sum()), float((x["net_M"] ** 2).sum())) for t, x in g.groupby("trade_id")}
    ids = sorted(gb)
    if len(ids) < 2:
        return np.nan, np.nan, np.nan
    xy = np.array([gb[t][0] for t in ids])
    xx = np.array([gb[t][1] for t in ids])
    idx = rng.integers(0, len(ids), (N_BOOT, len(ids)))
    vals = xy[idx].sum(1) / xx[idx].sum(1)
    return float(xy.sum() / xx.sum()), *np.percentile(vals[np.isfinite(vals)], [2.5, 97.5])


def fmt(e, lo, hi, p=None):
    if not np.isfinite(e):
        return "      n/a"
    s = f"{e:+6.2f} [{lo:+6.2f},{hi:+6.2f}]" if np.isfinite(lo) else f"{e:+6.2f} [   one trade ]"
    return s + (f" p={p:.3f}" if p is not None and np.isfinite(p) else "")


def side_table(cut, groups, rng, note=None):
    """groups: list of (label, DataFrame of club sides)."""
    log(f"\n{cut}")
    if note:
        log(f"  {note}")
    log(f"  {'group':<44}{'sides':>6}{'trades':>7}{'median':>8}{'IQR':>16}   {'forecast net':<30}{'outcome net, WAR':<30}"
        f"{'outcome net, Game Value':<30}")
    for lab, g in groups:
        nt = g["trade_id"].nunique()
        if len(g) == 0:
            log(f"  {lab:<44}{0:>6}{0:>7}")
            continue
        q1, med, q3 = np.percentile(g["net_M"], [25, 50, 75])
        r = {c: boot_mean(g, c, rng) for c in ("net_M", "out_net_M", "gv_net_M")}
        log(f"  {lab:<44}{len(g):>6}{nt:>7}{med:>+8.2f}{f'[{q1:+.2f},{q3:+.2f}]':>16}   "
            f"{fmt(*r['net_M']):<30}{fmt(*r['out_net_M']):<30}{fmt(*r['gv_net_M']):<30}")
        ROWS.append({"cut": cut, "group": lab, "unit": "club side", "n": len(g), "n_trades": nt, "median_forecast": med,
                     "q1": q1, "q3": q3,
                     **{f"{k}_{s}": v for k, c in (("forecast", "net_M"), ("out_war", "out_net_M"), ("out_gv", "gv_net_M"))
                        for s, v in zip(("mean", "lo", "hi", "p"), r[c])}})


def asset_table(cut, groups, rng, note=None):
    """groups: list of (label, DataFrame of assets with value, d_war, d_gv)."""
    log(f"\n{cut}")
    if note:
        log(f"  {note}")
    log(f"  {'group':<44}{'assets':>7}{'trades':>7}{'median fc':>10}   {'mean forecast':<15}{'outcome - forecast, WAR':<32}"
        f"{'outcome - forecast, Game Value':<32}")
    for lab, g in groups:
        if len(g) == 0:
            log(f"  {lab:<44}{0:>7}")
            continue
        r = {c: boot_mean(g, c, rng) for c in ("d_war", "d_gv")}
        log(f"  {lab:<44}{len(g):>7}{g['trade_id'].nunique():>7}{g['value'].median():>+10.2f}   {g['value'].mean():<+15.2f}"
            f"{fmt(*r['d_war']):<32}{fmt(*r['d_gv']):<32}")
        ROWS.append({"cut": cut, "group": lab, "unit": "asset", "n": len(g), "n_trades": g["trade_id"].nunique(),
                     "median_forecast": g["value"].median(), "forecast_mean": g["value"].mean(),
                     **{f"{k}_{s}": v for k, c in (("out_war", "d_war"), ("out_gv", "d_gv"))
                        for s, v in zip(("mean", "lo", "hi", "p"), r[c])}})


def slope_table(cut, groups, rng):
    log(f"\n{cut}")
    log(f"  {'group':<44}{'trades':>7}{'mean |forecast net|':>21}   {'slope, WAR outcome':<26}{'slope, Game Value outcome':<26}")
    for lab, g in groups:
        nt = g["trade_id"].nunique()
        if nt < 2:
            log(f"  {lab:<44}{nt:>7}")
            continue
        a_ = boot_slope(g, "out_net_M", rng)
        b_ = boot_slope(g, "gv_net_M", rng)
        size = g.groupby("trade_id")["net_M"].apply(lambda x: x.abs().max()).mean()
        log(f"  {lab:<44}{nt:>7}{size:>21.2f}   {a_[0]:+.2f} [{a_[1]:+.2f},{a_[2]:+.2f}]        "
            f"{b_[0]:+.2f} [{b_[1]:+.2f},{b_[2]:+.2f}]")
        ROWS.append({"cut": cut, "group": lab, "unit": "trade (slope)", "n": nt, "n_trades": nt, "mean_abs_forecast": size,
                     "out_war_mean": a_[0], "out_war_lo": a_[1], "out_war_hi": a_[2],
                     "out_gv_mean": b_[0], "out_gv_lo": b_[1], "out_gv_hi": b_[2]})


def main():
    rng = np.random.default_rng(SEED)
    log(SCRIPT_VERSION)
    log(f"  scope: {SCOPE}; reads {OUTPUT_DIR}")
    for f in ("backtest_log.txt", "backtest_log_gv_adj.txt"):
        log(f"  reads the run: {(OUTPUT_DIR / f).read_text(encoding='utf-8').splitlines()[0:2]}")
    # ---- club sides, both outcomes --------------------------------------------------------------------------------------
    s = pd.read_csv(OUTPUT_DIR / "backtest_sides.csv")
    sg = pd.read_csv(OUTPUT_DIR / "backtest_sides_gv_adj.csv")
    key = ["trade_id", "club"]
    assert (s[key + ["net_M"]].round(6) == sg[key + ["net_M"]].round(6)).all().all()   # GUARD: one forecast, same rows, both runs
    s["gv_net_M"] = sg["out_net_M"].values
    s = s[s["complete"]].copy()
    s["date"] = pd.to_datetime(s["trade_date"])
    # ---- assets, both outcomes ------------------------------------------------------------------------------------------
    a = pd.read_csv(OUTPUT_DIR / "backtest_assets.csv")
    ag = pd.read_csv(OUTPUT_DIR / "backtest_assets_gv_adj.csv")
    assert (a["asset_id"].values == ag["asset_id"].values).all() and np.allclose(           # GUARD: same assets, same forecast
        a["value_2025_cap_M"].fillna(0), ag["value_2025_cap_M"].fillna(0))
    a["value"] = a["value_2025_cap_M"]
    a["d_war"] = a["outcome_M"] - a["value"]
    a["d_gv"] = ag["outcome_M"].values - a["value"]
    a = a[a["trade_id"].isin(s["trade_id"]) & a["outcome_M"].notna()].copy()
    a["date"] = pd.to_datetime(a["trade_date"])

    # GUARD: the protocol's groups reproduce from these frames (recorded 2026-11-11, after pick_curve v1.12; on 2026-10-24 the
    # outcomes were +0.900 and GV +1.009: C1 275 sides +1.54 / +0.913 / GV +1.022;
    # C2 315 sides -0.57; C6 66 sides -2.95)
    ref = s[s["trade_date"] <= DECLARED_END]          # the declared window, whatever the scope: it must not have moved
    c1 = ref[ref["g_futures"]]
    assert len(c1) == 275 and abs(c1["net_M"].mean() - 1.54) < 0.005 and abs(c1["out_net_M"].mean() - 0.913) < 0.001
    assert abs(c1["gv_net_M"].mean() - 1.022) < 0.001
    assert ref["g_buyer"].sum() == 315 and abs(ref.loc[ref["g_buyer"], "net_M"].mean() + 0.57) < 0.005
    assert ref["g_clause"].sum() == 66 and abs(ref.loc[ref["g_clause"], "net_M"].mean() + 2.95) < 0.005
    log(f"  reference check PASS: the protocol's C1 (275 sides), C2 (315) and C6 (66) reproduce their recorded means")
    if SCOPE == "declared":
        s, a = s[s["trade_date"] <= DECLARED_END].copy(), a[a["trade_date"] <= DECLARED_END].copy()
    elif SCOPE == "new":
        s, a = s[s["trade_date"] > DECLARED_END].copy(), a[a["trade_date"] > DECLARED_END].copy()
    log(f"  {s['trade_id'].nunique()} complete trades, {len(s)} club sides, {len(a)} assets; $M at the 2025-26 cap")

    # ---- each player asset's facts at the trade ---------------------------------------------------------------------------
    pv = pd.read_csv(OUTPUT_DIR / "prospect_values.csv", low_memory=False)[
        ["asset_id", "nhl_id", "cap_hit", "draftYear", "pick"]].drop_duplicates("asset_id")
    pl = a[(a["asset_type"] == "player") & a["source"].str.startswith(("player model", "buried"))].merge(pv, on="asset_id", how="left")
    ls = pd.read_csv(OUTPUT_DIR / "contract_level_spine.csv", usecols=["nhl_id", "birthdate"]).drop_duplicates("nhl_id")
    pl["birth"] = pd.to_datetime(pl["nhl_id"].map(ls.set_index("nhl_id")["birthdate"]))
    pl["age"] = (pl["date"] - pl["birth"]).dt.days / 365.25
    ss = pd.read_csv(OUTPUT_DIR / "contract_season_spine.csv", low_memory=False)
    ss["signed"] = pd.to_datetime(ss["pp_signing_date"])
    by_ps = {k: g for k, g in ss.groupby(["nhl_id", "season_start"])}
    p17 = pd.read_csv(OUTPUT_DIR / "page_2017_values.csv").set_index("asset_id")

    def status(r):
        if r.source == "player model, rights":
            return "rights only (contract expired)", np.nan, np.nan
        if r.valuation_page == 2017:
            if r.asset_id not in p17.index or pd.isna(p17.at[r.asset_id, "contract_last_season"]):
                return "unknown", np.nan, np.nan
            x = p17.loc[r.asset_id]
            left, exp, elc = int(x["contract_last_season"]) - 2017 + 1, str(x["expiry"]), "Entry" in str(x["contract"])
            exp = "RFA" if exp.startswith("RFA") else "UFA"
            clause = np.nan
        else:
            g = by_ps.get((r.nhl_id, r.valuation_page)) if pd.notna(r.nhl_id) else None
            if g is None:
                return "unknown", np.nan, np.nan
            g = g[g["signed"] <= r.date] if (g["signed"] <= r.date).any() else g
            x = g.sort_values("signed").iloc[0]
            left, exp, elc = int(x["pp_signed_end"]) - int(r.valuation_page) + 1, str(x["pp_expiry"]), x["cs_entry_level"] == 1
            exp = "RFA" if exp == "RFA" else "UFA"
            clause = float(x["has_any_clause"] == 1)
        if elc:
            return "entry-level contract", left, clause
        if left <= 1:
            return ("final season, restricted at expiry" if exp == "RFA" else "final season, unrestricted at expiry"), left, clause
        return ("two seasons left" if left == 2 else "three or more seasons left"), left, clause
    st = [status(r) for r in pl.itertuples()]
    pl["cstatus"], pl["seasons_left"], pl["clause"] = [x[0] for x in st], [x[1] for x in st], [x[2] for x in st]
    tpv = pd.read_csv(OUTPUT_DIR / "traded_player_values.csv").set_index("asset_id")["n_contract_seasons"]
    chk = pl[pl["asset_id"].isin(tpv.dropna().index) & pl["seasons_left"].notna()]
    agree = (chk["seasons_left"] == chk["asset_id"].map(tpv)).sum()
    log(f"  check, seasons left against the player model's own count of contract seasons: equal for {agree} of {len(chk)}")
    log(f"  player assets {len(pl)}: age known {pl['age'].notna().sum()}, position known {pl['pos'].notna().sum()}, "
        f"status {pl['cstatus'].value_counts().to_dict()}")

    # the main player of each club side
    main_ = pl.sort_values("cap_hit", ascending=False, kind="stable").drop_duplicates(["trade_id", "acquiring_team"])
    m = s.merge(main_[["trade_id", "acquiring_team", "name", "pos", "age", "cstatus", "clause", "cap_hit", "pick", "draftYear",
                       "trailing_war"]].rename(columns={"acquiring_team": "club"}), on=key, how="left")
    two = m["n_clubs"] == 2
    log(f"  club sides with a main player: {m['name'].notna().sum()} of {len(m)}")

    # ======== 1 position ====================================================================================================
    side_table("1. POSITION of the main player the club received",
               [(k, m[m["pos"] == k]) for k in ("F", "D", "G")] + [("position unknown", m[m["name"].notna() & m["pos"].isna()])],
               rng, "goaltenders have no Game Value: their Game Value column is Bacon's WAR again")
    asset_table("1. POSITION, each player asset", [(k, pl[pl["pos"] == k]) for k in ("F", "D", "G")], rng)
    # ======== 2 age =========================================================================================================
    bands = (("23 and under", -1, 24), ("24 to 27", 24, 28), ("28 to 31", 28, 32), ("32 and over", 32, 99))
    side_table("2. AGE of the main player on the trade date",
               [(k, m[(m["age"] >= lo) & (m["age"] < hi)]) for k, lo, hi in bands] + [("age unknown", m[m["name"].notna() & m["age"].isna()])], rng)
    asset_table("2. AGE, each player asset", [(k, pl[(pl["age"] >= lo) & (pl["age"] < hi)]) for k, lo, hi in bands], rng)
    # ======== 3 asset class =================================================================================================
    t2 = m[two].copy()
    kinds = {}
    for tid, g in t2.groupby("trade_id"):
        if len(g) != 2:
            continue
        f, p_ = g["got_futures"].values, g["got_players"].values
        if g["g_futures"].any():
            kinds[tid] = "players for picks and prospects (C1)"
        elif p_.all() and not f.any():
            kinds[tid] = "players for players"
        elif f.all() and not p_.any():
            kinds[tid] = "picks and prospects both ways"
        elif (g["n_received"] == 0).any():
            kinds[tid] = "one club received nothing"
        else:
            kinds[tid] = "mixed (a club received both kinds)"
    t2["kind"] = t2["trade_id"].map(kinds)
    order = ["players for players", "players for picks and prospects (C1)", "picks and prospects both ways",
             "mixed (a club received both kinds)", "one club received nothing"]
    slope_table("3. ASSET CLASS: two-team trades by what changed hands (does the models' verdict come true)",
                [(k, t2[t2["kind"] == k]) for k in order], rng)
    side_table("3. ASSET CLASS: the club that received the picks and prospects",
               [("players for picks and prospects (C1)", t2[t2["g_futures"]]),
                ("mixed: the club that received more value in futures",
                 t2[(t2["kind"] == order[3])].loc[lambda d: d.groupby("trade_id")[["recv_picks_M", "recv_prospects_M"]]
                                                   .apply(lambda x: x.sum(axis=1).idxmax()).values])], rng,
               "the mixed row picks its club on the models' values, so its forecast net is partly selected")
    # ======== 4 contract status =============================================================================================
    sts = ["entry-level contract", "final season, restricted at expiry", "final season, unrestricted at expiry",
           "two seasons left", "three or more seasons left", "rights only (contract expired)", "unknown"]
    side_table("4. CONTRACT STATUS of the main player", [(k, m[m["cstatus"] == k]) for k in sts], rng)
    ufa = m["cstatus"] == sts[2]
    side_table("4. RENTALS: final season, unrestricted at expiry, by when traded",
               [("traded in-season (a rental)", m[ufa & m["during_regular_season"]]),
                ("traded in the off-season", m[ufa & ~m["during_regular_season"]])], rng)
    asset_table("4. CONTRACT STATUS, each player asset", [(k, pl[pl["cstatus"] == k]) for k in sts], rng)
    # ======== 5b former top prospects =======================================================================================
    pcp = pd.read_csv(OUTPUT_DIR / "pick_curve_players.csv")
    pcs = pd.read_csv(OUTPUT_DIR / "pick_curve_seasons.csv")
    top = pcp[(pcp["pick"] <= 15) & pcp["draftYear"].between(2005, 2012) & (pcp["is_goalie"] != True)]   # noqa: E712
    grid = [(r.draftYear, r.pick, y) for r in top.itertuples() for y in range(int(r.draftYear) + 4, min(2016, int(r.window_end) - 1) + 1)]
    w = pcs.set_index(["draftYear", "pick", "season"])["war_82"]
    bench = float(np.mean([w.get(k, 0.0) for k in grid]))
    log(f"\n5b. FORMER TOP PROSPECTS. Benchmark: top-15 skaters of the 2005-2012 drafts averaged {bench:.3f} WAR per 82 a season in "
        f"D+5 and later while under club control, through 2016-17 ({len(grid)} player-seasons, {len(top)} players; a season out of the NHL counts zero)")
    tp_ = pl[(pl["pick"] <= 15) & ((pl["valuation_page"] - pl["draftYear"]) >= 4) & (pl["pos"] != "G")]
    under = tp_[tp_["trailing_war"] < bench]
    over = tp_[tp_["trailing_war"] >= bench]
    log(f"  top-15 picks traded in D+5 or later: {len(tp_)} assets, {tp_['name'].nunique()} players; below the benchmark {len(under)} "
        f"({under['name'].nunique()} players); at or above {len(over)}; no trailing total {tp_['trailing_war'].isna().sum()}")
    ks = lambda d: m.merge(d[["trade_id", "acquiring_team"]].drop_duplicates().rename(columns={"acquiring_team": "club"}), on=key)  # noqa: E731
    side_table("5b. the club that received him", [("top-15 pick, below the benchmark", ks(under)),
                                                  ("top-15 pick, at or above the benchmark", ks(over))], rng)
    asset_table("5b. each such player asset", [("top-15 pick, below the benchmark", under), ("top-15 pick, at or above the benchmark", over)], rng)
    # ======== 6 timing ======================================================================================================
    dl = [pd.Timestamp(d) for d in DEADLINES]
    in_win = m["date"].map(lambda d: any(x - pd.Timedelta(days=13) <= d <= x for x in dl))
    m["timing"] = np.where(~m["during_regular_season"], "off-season", np.where(in_win, "deadline window (14 days)", "rest of the regular season"))
    tim = ["off-season", "rest of the regular season", "deadline window (14 days)"]
    slope_table("6. TIMING: does the models' verdict come true", [(k, m[m["timing"] == k]) for k in tim], rng)
    side_table("6. TIMING: the club higher in the standings (in-season two-team trades)",
               [(k, m[m["g_buyer"] & (m["timing"] == k)]) for k in tim[1:]], rng)
    # ======== 7 buyers ======================================================================================================
    gap = m[two & m["standing"].notna()].groupby("trade_id")["standing"].transform(lambda x: x.max() - x.min())
    m["gap"] = gap
    b = m[m["g_buyer"]]
    med = b["gap"].median()
    log(f"\n7. the median gap in points percentage between the two clubs: {med:.3f}")
    side_table("7. BUYERS: the club higher in the standings",
               [("all (the protocol's C2)", b), (f"gap above {med:.3f}", b[b["gap"] > med]), (f"gap at or below {med:.3f}", b[b["gap"] <= med]),
                ("received a rental", b[b["cstatus"] == sts[2]]),
                ("received a rental in the deadline window", b[(b["cstatus"] == sts[2]) & (b["timing"] == tim[2])]),
                ("received no rental", b[b["cstatus"] != sts[2]])], rng)
    # ======== 9 retention ===================================================================================================
    r_ = m[m["g_retained"]]
    side_table("9. RETENTION: the club that retained salary",
               [("all (the protocol's C4)", r_)] + [(k, r_[r_["timing"] == k]) for k in tim] +
               [("in a three-team trade", r_[r_["n_clubs"] == 3]),
                ("trade seasons to 2021-22", r_[r_["date"] < "2022-07-01"]),
                ("trade seasons 2022-23 to 2024-25", r_[(r_["date"] >= "2022-07-01") & (r_["date"] < "2025-07-01")]),
                ("trade season 2025-26", r_[r_["date"] >= "2025-07-01"])], rng)
    log(f"  three-team trades in the back-test: {m.loc[m['n_clubs'] == 3, 'trade_id'].nunique()}")
    # ======== 10 clauses ====================================================================================================
    big = m[(m["cap_hit"] >= 3_000_000) & (m["valuation_page"] >= 2018)]
    side_table("10. CLAUSES: main player with a cap hit of $3M or more, 2018-19 on",
               [("no-trade or no-move clause", big[big["clause"] == 1]), ("no clause", big[big["clause"] == 0])], rng,
               f"median cap hit: clause ${big.loc[big['clause'] == 1, 'cap_hit'].median() / 1e6:.2f}M, none "
               f"${big.loc[big['clause'] == 0, 'cap_hit'].median() / 1e6:.2f}M; median age {big.loc[big['clause'] == 1, 'age'].median():.1f} and "
               f"{big.loc[big['clause'] == 0, 'age'].median():.1f}")
    # ======== 11 era ========================================================================================================
    m["era"] = np.where(m["date"] < PAUSE, "before 2020-03-12", np.where(m["date"] < "2022-07-01", "2020-03-12 to 2022-06-30 (flat cap)", "2022-07-01 on"))
    eras = ["before 2020-03-12", "2020-03-12 to 2022-06-30 (flat cap)", "2022-07-01 on"]
    slope_table("11. CAP ERA: does the models' verdict come true", [(k, m[m["era"] == k]) for k in eras], rng)
    side_table("11. CAP ERA: the club that received picks and prospects for players (C1)",
               [(k, m[m["g_futures"] & (m["era"] == k)]) for k in eras], rng)
    side_table("11. CAP ERA: the club higher in the standings (C2)", [(k, m[m["g_buyer"] & (m["era"] == k)]) for k in eras], rng)
    # ======== 12 over time ==================================================================================================
    m["season"] = m["date"].map(lambda d: d.year if d.month >= 7 else d.year - 1)
    seas = sorted(m["season"].unique())
    slope_table("12. OVER TIME, by trade season (starting year): size of the models' verdict and whether it comes true",
                [(f"{y}-{str(y + 1)[2:]}", m[m["season"] == y]) for y in seas], rng)
    side_table("12. OVER TIME: the club that received picks and prospects for players (C1)",
               [(f"{y}-{str(y + 1)[2:]}", m[m["g_futures"] & (m["season"] == y)]) for y in seas], rng)
    tr = m.groupby("trade_id").agg(size=("net_M", lambda x: x.abs().max()), season=("season", "first"))
    ids = tr.index.values
    sl = lambda d: float(np.polyfit(d["season"], d["size"], 1)[0])  # noqa: E731
    bs = np.array([sl(tr.loc[ids[rng.integers(0, len(ids), len(ids))]]) for _ in range(N_BOOT)])
    log(f"  trend of the absolute forecast net per trade: {sl(tr):+.3f} $M a season [{np.percentile(bs, 2.5):+.3f}, {np.percentile(bs, 97.5):+.3f}]")
    ROWS.append({"cut": "12. trend of |forecast net| per trade, $M a season", "group": "all", "unit": "trade", "n": len(tr),
                 "forecast_mean": sl(tr), "forecast_lo": np.percentile(bs, 2.5), "forecast_hi": np.percentile(bs, 97.5)})
    # ======== 13 quantity for quality =======================================================================================
    q = []
    for tid, g in m[two].groupby("trade_id"):
        if len(g) == 2 and sorted(g["n_received"])[0] == 1 and sorted(g["n_received"])[1] >= 2:
            q.append((g["n_received"].idxmin(), sorted(g["n_received"])[1]))
    qd = m.loc[[i for i, _ in q]].assign(other=[n for _, n in q])
    side_table("13. QUANTITY FOR QUALITY: the club that received one asset for two or more",
               [("one for two or more", qd), ("one for two", qd[qd["other"] == 2]), ("one for three or more", qd[qd["other"] >= 3]),
                ("the single asset is a player", qd[qd["got_players"]]), ("the single asset is a pick or prospect", qd[~qd["got_players"]])], rng)
    # ======== 14 future picks ===============================================================================================
    tp = pd.read_csv(OUTPUT_DIR / "traded_pick_values.csv")
    pk = a[a["asset_type"] == "pick"].merge(tp[["asset_id", "pick_year", "pick_round", "conditional", "method", "projected_slot",
                                                "actual_slot"]], on="asset_id")
    de = {y: pd.Timestamp(d) for y, d in DRAFT_END.items()}
    pk["next_draft"] = pk["date"].map(lambda d: min(y for y, e in de.items() if e >= d))
    pk["years_out"] = pk["pick_year"] - pk["next_draft"]
    assert (pk["years_out"] >= 0).all()                                                    # GUARD: no pick traded after its draft
    asset_table("14a. FUTURE PICKS by drafts between the trade and the pick (0 = the next draft)",
                [("the next draft", pk[pk["years_out"] == 0]), ("one draft later", pk[pk["years_out"] == 1]),
                 ("two or more drafts later", pk[pk["years_out"] >= 2])], rng)
    kp = lambda d: m.merge(d[["trade_id", "acquiring_team"]].drop_duplicates().rename(columns={"acquiring_team": "club"}), on=key)  # noqa: E731
    side_table("14a. the club that received a pick, by its most distant pick received",
               [(lab, kp(pk.loc[pk.groupby(["trade_id", "acquiring_team"])["years_out"].transform("max").pipe(f)]))
                for lab, f in (("the next draft", lambda x: x == 0), ("one draft later", lambda x: x == 1),
                               ("two or more drafts later", lambda x: x >= 2))], rng)
    ra = pk[pk["method"].str.startswith("round average") & pk["actual_slot"].notna()].copy()
    ra["mid"] = (ra["pick_round"] - 1) * np.where(ra["pick_year"] <= 2021, 31, 32) + np.where(ra["pick_year"] <= 2021, 16, 16.5)
    ra["slot_gap"] = ra["actual_slot"] - ra["mid"]
    log("\n14b. PICKS VALUED AT THE ROUND AVERAGE: the selection it became minus the round's middle selection (below zero = an earlier, better pick than priced)")
    log(f"  {'group':<44}{'picks':>7}{'trades':>7}   mean gap in selections")
    for lab, g in (("all", ra), ("the next draft", ra[ra["years_out"] == 0]), ("one draft later", ra[ra["years_out"] == 1]),
                   ("two or more drafts later", ra[ra["years_out"] >= 2]), ("round 1 only", ra[ra["pick_round"] == 1]),
                   ("rounds 1 and 2", ra[ra["pick_round"] <= 2])):
        e = boot_mean(g, "slot_gap", rng)
        log(f"  {lab:<44}{len(g):>7}{g['trade_id'].nunique():>7}   {fmt(*e)}")
        ROWS.append({"cut": "14b. selection minus the round's middle", "group": lab, "unit": "pick", "n": len(g),
                     "n_trades": g["trade_id"].nunique(), **{f"forecast_{s}": v for s, v in zip(("mean", "lo", "hi", "p"), e)}})
    asset_table("14c. CONDITIONAL PICKS (valued as unconditional)", [("conditional", pk[pk["conditional"]]), ("not conditional", pk[~pk["conditional"]])], rng)
    slope_table("14c. trades with and without a conditional pick",
                [("with a conditional pick", m[m.groupby("trade_id")["has_conditional_pick"].transform("any")]),
                 ("without", m[~m.groupby("trade_id")["has_conditional_pick"].transform("any")])], rng)
    # ======== 15 late picks =================================================================================================
    pk["slot"] = pk["projected_slot"].fillna(pk["actual_slot"])
    asset_table("15. PICKS BY ROUND",
                [("round 1", pk[pk["pick_round"] == 1]), ("round 2", pk[pk["pick_round"] == 2]), ("rounds 3 and 4", pk[pk["pick_round"].isin([3, 4])]),
                 ("round 5", pk[pk["pick_round"] == 5]), ("rounds 6 and 7", pk[pk["pick_round"] >= 6]),
                 ("selection 151 or later (projected, else actual)", pk[pk["slot"] >= 151])], rng)
    late_only = m[(m["n_received"] > 0) & two].merge(
        a.assign(late=(a["asset_type"] == "pick") & a["asset_id"].isin(pk.loc[pk["pick_round"] >= 6, "asset_id"]))
         .loc[lambda d: d["asset_type"] != "retained salary"].groupby(["trade_id", "acquiring_team"])["late"].all()
         .rename("only_late").reset_index().rename(columns={"acquiring_team": "club"}), on=key)
    side_table("15. the club whose whole return was picks in rounds 6 and 7", [("only round 6-7 picks received", late_only[late_only["only_late"]])], rng)

    pd.DataFrame(ROWS).to_csv(OUTPUT_DIR / f"backtest_cuts{SUFFIX}.csv", index=False)
    (OUTPUT_DIR / f"backtest_cuts{SUFFIX}_log.txt").write_text("\n".join(LOG), encoding="utf-8")
    log(f"\nwrote backtest_cuts.csv ({len(ROWS)} rows) and backtest_cuts_log.txt")


if __name__ == "__main__":
    main()
