"""
stata_export_backtest.py -- the back-test's tests and the Game Value chain's regressions as flat CSVs, for Stata (v1.0).

WHY: every regression the model runs should be reproducible by hand in Stata from files on disk (supervisor meeting,
2026-10-23; Thomas: "create stata csvs for everything"). stata_export.py covers the draft pick curve and the prospect
model, stata_export_players.py the player model; this script covers the back-test (backtest.py) and the regressions of
the game-level chain behind its Game Value check (metric_assembly.py, replacement_rebase.py).

WHERE THE ROWS COME FROM
  The back-test: its own outputs, backtest_sides*.csv and backtest_assets*.csv (backtest.analyse writes the club sides
  with every group flag; the Game Value runs' outcomes are joined beside the WAR run's). Nothing is recomputed.
  Game Value: the game-log database (GAMELOG_DB), opened read-only, with metric_assembly's own queries.

OUTPUTS (OUTPUT_DIR/stata/; codebook: 40_DOCS/Stata_Data_Codebook.md):
  backtest_club_sides.csv   one row per club side of each trade: forecast net, outcome net (WAR; Game Value adjusted
                            and raw beside it), the group flags.
  backtest_assets.csv       one row per traded asset: its class, forecast and outcome, and whether its trade is
                            complete (test B).
  gv_team_games.csv         one row per team and regular-season game: summed Game Value, in-play goal differential.
  gv_team_seasons.csv       one row per team-season: wins, in-play goal differential, summed Game Value.
  stata_export_backtest_log.txt

CHECKS (each must PASS or the script stops; each read back from the CSV):
  1. Test A's slope, correlation and agreement share, test A's sensitivities and timing slopes, test B's class means
     and test C's group means, from the CSVs, equal backtest_results.csv's estimates (to 1e-9), for the WAR run and
     both Game Value runs. The intervals and p-values come from 2,000 resamples of trades (numpy's generator, seed
     20261020); they are not recomputed here, and a Stata bootstrap draws different resamples.
  2. The team-game and team-season validation regressions and the pooled goals per win, from the CSVs, equal
     metric_validation.csv (to its four decimals), and the goals per win of each season equal
     goals_per_win_by_season.csv (to its three).

Run from the repo root:  python 20_CODE/stata_export_backtest.py   (after backtest.py and its Game Value runs)
"""

import os
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
load_dotenv()
import trade_sides as TSD                        # noqa: E402

SCRIPT_VERSION = "stata_export_backtest.py v1.0 (2026-10-23)"
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
GAMELOG_DB = Path(os.environ["GAMELOG_DB"])
OUT = OUTPUT_DIR / "stata"
RUNS = {"": "war", "_gv_adj": "gv_adj", "_gv_raw": "gv_raw"}     # backtest.py's output suffix -> column suffix
TOL = 1e-9
LOG = []


def log(s=""):
    print(s, flush=True)
    LOG.append(str(s))


# =============================== 1. the back-test ======================================================================
def backtest():
    sides, assets = None, None
    for suf, lab in RUNS.items():
        s = pd.read_csv(OUTPUT_DIR / f"backtest_sides{suf}.csv")
        a = pd.read_csv(OUTPUT_DIR / f"backtest_assets{suf}.csv")
        log(f"  read backtest_sides{suf}.csv ({len(s):,} club sides) and backtest_assets{suf}.csv ({len(a):,} assets)")
        if sides is None:
            sides = s.copy()
            sides.columns = [c.lower() for c in sides.columns]
            sides = sides.rename(columns={"net_m": "forecast_net_m", "out_net_m": "outcome_net_m",
                                          "real_net_m": "realised_net_m", "miss_m": "miss_m"})
            assets = a[["asset_id", "trade_id", "trade_date", "asset_type", "name", "from_team", "acquiring_team",
                        "source", "value_2025_cap_M", "realised_M", "outcome_M", "trailing_war"]].copy()
            assets["asset_class"] = assets["source"].map(TSD.asset_class)
            assets = assets.rename(columns={"value_2025_cap_M": "forecast_m", "realised_M": "realised_m",
                                            "outcome_M": "outcome_m"})
            continue
        key = ["trade_id", "club"]
        assert (s[key].values == sides[key].values).all() and (s["net_M"].values == sides["forecast_net_m"].values).all()
        assert (s["complete"].values == sides["complete"].values).all()
        sides[f"outcome_net_m_{lab}"] = s["out_net_M"].values
        sides[f"realised_net_m_{lab}"] = s["real_net_M"].values
        assert (a["asset_id"].values == assets["asset_id"].values).all()
        assets[f"outcome_m_{lab}"] = a["outcome_M"].values
        assets[f"realised_m_{lab}"] = a["realised_M"].values
    for c in [c for c in sides.columns if sides[c].dtype == bool]:
        sides[c] = sides[c].astype(int)
    assets["complete_trade"] = assets["trade_id"].isin(set(sides.loc[sides["complete"] == 1, "trade_id"])).astype(int)
    sides.to_csv(OUT / "backtest_club_sides.csv", index=False)
    assets.to_csv(OUT / "backtest_assets.csv", index=False)
    S = pd.read_csv(OUT / "backtest_club_sides.csv")
    A = pd.read_csv(OUT / "backtest_assets.csv")
    log(f"  wrote backtest_club_sides.csv ({len(S):,} rows) and backtest_assets.csv ({len(A):,} rows)")

    for suf, lab in RUNS.items():
        res = pd.read_csv(OUTPUT_DIR / f"backtest_results{suf}.csv")
        want = {(r.test, r.group): r.estimate for r in res.itertuples()}
        y = "outcome_net_m" if lab == "war" else f"outcome_net_m_{lab}"
        yr = "realised_net_m" if lab == "war" else f"realised_net_m_{lab}"
        ya = "outcome_m" if lab == "war" else f"outcome_m_{lab}"
        c = S[S["complete"] == 1]
        trades = set(c["trade_id"])

        def slope(d, ycol=y):
            return float((d["forecast_net_m"] * d[ycol]).sum() / (d["forecast_net_m"] ** 2).sum())

        fav = c.loc[c.groupby("trade_id")["forecast_net_m"].idxmax()]
        fav = fav[fav["forecast_net_m"] > 0]
        got = {("A. slope of outcome net on forecast net (1 = the forecast's gaps come true)", "all complete trades"): slope(c),
               ("A. correlation of forecast net and outcome net", "all complete trades"):
                   float(np.corrcoef(c["forecast_net_m"], c[y])[0, 1]),
               ("A. share of trades whose favoured club came out ahead (0.5 = a coin)", "all complete trades"):
                   float((fav[y] > 0).mean()),
               ("A, sensitivity: realised only (nothing revalued)", "all complete trades"): slope(c, yr),
               ("A, sensitivity: trades with a conditional pick left out", "no conditional pick"):
                   slope(c[~c["trade_id"].isin(set(c.loc[c["has_conditional_pick"] == 1, "trade_id"]))]),
               ("C7. slope by timing", "in-season"): slope(c[c["during_regular_season"] == 1]),
               ("C7. slope by timing", "off-season"): slope(c[c["during_regular_season"] == 0])}
        assert set(A.loc[A["complete_trade"] == 1, "trade_id"]) <= trades
        ac = A[(A["complete_trade"] == 1) & A[ya].notna()]
        for k in ("players", "picks", "prospects", "retained"):
            g = ac[ac["asset_class"] == k]
            got[("B. mean outcome minus forecast per asset", k)] = float((g[ya] - g["forecast_m"]).mean())
        groups = {"g_futures": "C1. received the picks and prospects for players",
                  "g_buyer": "C2. higher in the standings, in-season two-team trades",
                  "g_star": "C3. received a skater with a 3+ trailing WAR total", "g_retained": "C4. retained salary",
                  "g_nothing_back": "C5. received nothing recorded",
                  "g_clause": "C6. received a player with a no-trade or no-move clause"}
        for col, labg in groups.items():
            gs = c[c[col] == 1]
            if not len(gs):
                continue
            got[(f"{labg}: forecast", col)] = float(gs["forecast_net_m"].mean())
            got[(f"{labg}: outcome", col)] = float(gs[y].mean())
            got[(f"{labg}: outcome - forecast", col)] = float((gs[y] - gs["forecast_net_m"]).mean())
        n = 0
        for k_, v in got.items():
            assert k_ in want, (lab, k_)
            assert abs(v - want[k_]) < TOL, (lab, k_, v, want[k_])
            n += 1
        log(f"  check 1 ({lab}): {n} estimates from the CSVs equal backtest_results{suf}.csv (PASS); test A's slope "
            f"{got[next(iter(got))]:.4f} on {len(trades)} complete trades")


# =============================== 2. the Game Value chain ================================================================
def game_value():
    con = sqlite3.connect(f"file:{GAMELOG_DB.as_posix()}?mode=ro", uri=True)
    tg = pd.read_sql("""SELECT v.game_id, g.season, v.team, SUM(v.game_value) AS game_value_sum,
                               g.away_team, g.home_team, g.away_score, g.home_score, g.last_period
                        FROM player_game_value v JOIN games g ON g.game_id = v.game_id
                        WHERE v.game_type = 2 GROUP BY v.game_id, v.team""", con)       # metric_assembly step 5B
    tg = tg[tg["away_score"].notna() & tg["home_score"].notna()].copy()
    a, h = tg["away_score"].astype(int), tg["home_score"].astype(int)
    so = tg["last_period"] == "SO"                                                         # the shootout winner's +1 out
    a2, h2 = a - (so & (a > h)).astype(int), h - (so & (a <= h)).astype(int)
    tg["goal_diff_in_play"] = np.where(tg["team"] == tg["home_team"], h2 - a2, a2 - h2)
    tg["season"] = tg["season"].astype(str)
    tg = tg[["game_id", "season", "team", "game_value_sum", "goal_diff_in_play"]]
    tg.to_csv(OUT / "gv_team_games.csv", index=False)

    gm = pd.read_sql("SELECT game_id, season, away_team, home_team, away_score, home_score, last_period FROM games "
                     "WHERE CAST(game_type AS INTEGER) = 2", con)                         # metric_assembly step 5C
    ts = defaultdict(lambda: [0, 0])
    for r in gm.itertuples():
        if r.away_score is None or r.home_score is None or pd.isna(r.away_score) or pd.isna(r.home_score):
            continue
        asc, hsc = int(r.away_score), int(r.home_score)
        winner = r.home_team if hsc > asc else r.away_team
        x2, y2 = asc, hsc
        if r.last_period == "SO":
            if asc > hsc:
                x2 -= 1
            else:
                y2 -= 1
        ts[(str(r.season), r.home_team)][0] += int(winner == r.home_team)
        ts[(str(r.season), r.home_team)][1] += y2 - x2
        ts[(str(r.season), r.away_team)][0] += int(winner == r.away_team)
        ts[(str(r.season), r.away_team)][1] += x2 - y2
    gvs = tg.groupby(["season", "team"]).agg(game_value_sum=("game_value_sum", "sum"),
                                             gv_goal_diff=("goal_diff_in_play", "sum"))
    tsd = pd.DataFrame([{"season": s, "team": t, "wins": v[0], "goal_diff_in_play": v[1]} for (s, t), v in ts.items()])
    tsd = tsd.merge(gvs.reset_index(), on=["season", "team"], how="left")
    tsd.to_csv(OUT / "gv_team_seasons.csv", index=False)
    G = pd.read_csv(OUT / "gv_team_games.csv", dtype={"season": str})
    T = pd.read_csv(OUT / "gv_team_seasons.csv", dtype={"season": str})
    log(f"  wrote gv_team_games.csv ({len(G):,} team-games) and gv_team_seasons.csv ({len(T):,} team-seasons)")

    def fit(y, x):
        X = np.column_stack([np.ones(len(x)), x])
        b = np.linalg.lstsq(X, y, rcond=None)[0]
        r2 = 1 - float(((y - X @ b) ** 2).sum()) / float(((y - y.mean()) ** 2).sum())
        return b, r2

    mv = pd.read_csv(OUTPUT_DIR / "metric_validation.csv").set_index("check")["value"].astype(float)
    b, r2 = fit(G["goal_diff_in_play"].to_numpy(float), G["game_value_sum"].to_numpy(float))
    sv = T.dropna(subset=["game_value_sum"])
    bs, r2s = fit(sv["gv_goal_diff"].to_numpy(float), sv["game_value_sum"].to_numpy(float))
    bg, _ = fit(T["wins"].to_numpy(float), T["goal_diff_in_play"].to_numpy(float))
    got = {"teamgame_regression_slope": (b[1], 4), "teamgame_regression_intercept": (b[0], 4),
           "teamgame_regression_r2": (r2, 4), "teamseason_regression_slope": (bs[1], 4),
           "teamseason_regression_r2": (r2s, 4), "goals_per_win": (1 / bg[1], 3),
           "team_games_in_regression": (len(G), 0)}
    for k_, (v, dp) in got.items():
        assert round(float(v), dp) == round(float(mv[k_]), dp), (k_, v, mv[k_])
    log(f"  check 2: team-game slope {b[1]:.4f} (R-squared {r2:.4f}), team-season slope {bs[1]:.4f} (R-squared "
        f"{r2s:.4f}), goals per win {1 / bg[1]:.3f} on {len(T)} team-seasons = metric_validation.csv (PASS)")
    gw = pd.read_csv(OUTPUT_DIR / "goals_per_win_by_season.csv", dtype={"season": str})
    gw = gw[gw["season"] != "POOLED"]                                   # the pooled row is checked above (5.903)
    for r in gw.itertuples():
        x = T[T["season"] == r.season]
        b1, _ = fit(x["wins"].to_numpy(float), x["goal_diff_in_play"].to_numpy(float))
        assert len(x) == r.n_teams and round(1 / b1[1], 3) == round(r.goals_per_win, 3), (r.season, 1 / b1[1])
    log(f"  check 2: goals per win in each of {len(gw)} seasons = goals_per_win_by_season.csv (PASS)")


def main():
    log(SCRIPT_VERSION)
    OUT.mkdir(parents=True, exist_ok=True)
    log("\nTHE BACK-TEST")
    backtest()
    log("\nTHE GAME VALUE CHAIN")
    game_value()
    (OUT / "stata_export_backtest_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
