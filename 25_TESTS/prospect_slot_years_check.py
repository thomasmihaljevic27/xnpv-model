"""
prospect_slot_years_check.py -- the prospect model's simplest version, measured: what a drafted player who
is still a prospect is worth from his slot, by seasons since his draft.

DECIDED (Thomas, 2026-10-14, the opening questions of the prospect model; MODEL_DIRECTIVES directive 6):
  * a prospect's value is in the pick curve's currency: his remaining NHL seasons priced on the contract line
    minus his cost (entry-level deal, then control seasons at the qualifying offer or the arbitration price),
    to the end of club control, at the 2025-26 cap;
  * a prospect is a player the player model does not take yet. Skaters: no NHL season of 10+ games in the
    three before the valuation season (forecast_config.MIN_GP, skater_forecast's three-season anchor).
    Goalies: the goalie forecast takes any NHL season in the three before, walking back up to three more when
    the last is missing (contract_npv.shrunk_projection, STALE_MAXBACK 3), so a goalie is a prospect only
    with no NHL game in the six seasons before;
  * the simplest version: his slot's star chance x a star value re-fitted for each season since the draft on
    the drafted players still prospects then, seasons 4 and later pooled into one;
  * the overlap (a 2007-2017 draftee sits inside the fit that values him) is a stated limitation, as for
    picks, with the value with his draft left out reported beside.

WHAT THIS SCRIPT DOES
  1. For each drafted player of 2007-2017 (pick_curve_players.csv) and each k = 0..7, the valuation season is
     y = draft year + k (k = 0: the season starting the autumn after his draft, the pick curve's own first
     season). He is a prospect at k under the rule above, read from pick_curve_seasons.csv (seasons before y).
  2. His remaining surplus is the sum of pick_curve_seasons.csv's surplus_2025_cap over seasons y and later:
     the pick curve's own priced seasons (adopted arbitration cost), with lapsed rights zeroed as the pick
     curve zeroes them (route "lapsed" or "drafted twice (earlier pick)"). Season y is counted in full.
  3. The star value for k is pick_curve.fit_scale() on the prospects at k: remaining surplus on Bacon's star
     chance, through zero, draft-year indicators that sum to zero, robust (HC1) errors. Seasons 4+ are one
     fit on the stacked rows (k = 4..7 while y <= 2025), errors clustered by player.
  4. Leave-one-draft-out: each fit again without each draft; the range is reported beside (the limitation).

v1.1 (2026-10-15, Thomas): drafted players who died before reaching the NHL (pick_curve_players.csv
excluded_deceased, six players) are left out, as from every fit. v1.0's figures reproduce from git before this.
GUARD: at k = 0 every drafted player is a prospect and his remaining surplus is his whole surplus, so the
fit must reproduce pick_curve_scales.csv's main star value (asserted to 1e-9).

TRAILING WEIGHTING CHECK (directive 6): this script reads no trailing total itself. The surplus it sums
carries the pick curve's arbitration price, which reads the forecast's 50/30/20 (pick_curve.py v1.5).

INPUTS: OUTPUT_DIR/pick_curve_players.csv, pick_curve_seasons.csv, pick_curve_scales.csv (pick_curve.py v1.5).
OUTPUTS: OUTPUT_DIR/prospect_slot_years.csv (one row per fit), prospect_slot_years_rows.csv (one row per
player and k), prospect_slot_years_log.txt.
Run from the repo root:  python 25_TESTS/prospect_slot_years_check.py
"""

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv

SCRIPT_VERSION = "prospect_slot_years_check.py v1.3 (2026-10-18)"   # v1.3: rows past club control left out; v1.2: no draft-year terms
load_dotenv()
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


log(SCRIPT_VERSION)
F = {k: OUTPUT_DIR / f"pick_curve_{k}.csv" for k in ("players", "seasons", "scales")}
for k, p in F.items():
    log(f"  input {k}: {p.resolve()}  (modified {pd.Timestamp(p.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M})")

LAST_START = 2025                     # 2025-26, the last season in the data (start year)
SKATER_GP, SKATER_BACK = 10, 3        # skater forecast: a 10+ game season in the three before
GOALIE_BACK = 6                       # goalie forecast: any NHL game in the three before, walk-back up to three more
POOL_FROM, K_MAX = 4, 7
LAPSED = ("lapsed", "drafted twice (earlier pick)")

p = pd.read_csv(F["players"])
p = p[~p["excluded_deceased"].astype(bool)]           # v1.1: drafted players who died before the NHL
s = pd.read_csv(F["seasons"])
main_star = pd.read_csv(F["scales"]).set_index("scale_kind").loc["main", "scale_M"]
# lapsed rights are worth zero to the pick (pick_curve step 8): zero every season's surplus for them
lapsed = p.loc[p["route"].isin(LAPSED), ["draftYear", "pick"]].assign(lapsed=True)
s = s.merge(lapsed, on=["draftYear", "pick"], how="left")
s["sur_M"] = np.where(s["lapsed"].fillna(False).astype(bool), 0.0, s["surplus_2025_cap"] / 1e6)
by_player = {key: g for key, g in s.groupby(["draftYear", "pick"])}
EMPTY = s.iloc[0:0]

rows = []
for r in p.itertuples():
    mine = by_player.get((r.draftYear, r.pick), EMPTY)
    for k in range(0, K_MAX + 1):
        y = r.draftYear + k
        if y > LAST_START:
            break
        before = mine[mine["season"] < y]
        if r.is_goalie:
            taken = (before["season"] >= y - GOALIE_BACK).any()            # any NHL game (rows exist only if gp > 0)
        else:
            taken = ((before["season"] >= y - SKATER_BACK) & (before["gp"] >= SKATER_GP)).any()
        # v1.3 (2026-10-18, the bug sweep): a season past the end of his club control (pick_curve window_end) is not a
        # prospect row: its remaining surplus is zero by construction, and prospect_values.py values such a prospect at
        # zero by rule, so the fit must not learn from it (116 rows, all four or more seasons after the draft)
        rows.append({"draftYear": r.draftYear, "pick": r.pick, "player": r.player, "is_goalie": r.is_goalie,
                     "p_star": r.p_star, "k": k, "season": y, "prospect": (not taken) and y < r.window_end,
                     "past_control": y >= r.window_end,
                     "nhl_games_before": float(before["gp"].sum()),
                     "remaining_M": float(mine.loc[mine["season"] >= y, "sur_M"].sum())})
d = pd.DataFrame(rows)


def fit(frame, cluster=False):
    """pick_curve.fit_scale on remaining surplus: through zero, no draft-year terms (v1.2)."""
    X = np.column_stack([frame["p_star"].values])
    if cluster:
        groups = pd.factorize(frame["draftYear"].astype(str) + "-" + frame["pick"].astype(str))[0]
        m = sm.OLS(frame["remaining_M"].values, X).fit(cov_type="cluster", cov_kwds={"groups": groups})
    else:
        m = sm.OLS(frame["remaining_M"].values, X).fit(cov_type="HC1")
    return m.params[0], m.bse[0]


P1 = float(p.loc[p["pick"] == 1, "p_star"].iloc[0])
out = []
groups = [(str(k), d[(d["k"] == k) & d["prospect"]], False) for k in range(POOL_FROM)]
groups.append((f"{POOL_FROM}+", d[(d["k"] >= POOL_FROM) & d["prospect"]], True))
for label, g, clus in groups:
    b, se = fit(g, clus)
    lodo = [fit(g[g["draftYear"] != c], clus)[0] for c in sorted(g["draftYear"].unique())]
    out.append({"seasons_since_draft": label, "rows": len(g), "players": g[["draftYear", "pick"]].drop_duplicates().shape[0],
                "drafts": g["draftYear"].nunique(), "star_value_M": b, "se_M": se, "pick1_value_M": b * P1,
                "lodo_min_M": min(lodo), "lodo_max_M": max(lodo),
                "top10_prospects": int(g.loc[g["pick"] <= 10, ["draftYear", "pick"]].drop_duplicates().shape[0]),
                "share_with_nhl_games": float((g["nhl_games_before"] > 0).mean())})
o = pd.DataFrame(out)

assert abs(o.loc[0, "star_value_M"] - main_star) < 1e-9, (o.loc[0, "star_value_M"], main_star)   # GUARD
log(f"  guard: at the draft the fit reproduces the pick curve's star value {main_star:.4f} (PASS)")

log("\nWHO IS A PROSPECT, by seasons since the draft (drafted players 2007-2017)")
for k, g in d.groupby("k"):
    log(f"  {k}: {len(g):5,} players; prospects {int(g['prospect'].sum()):5,}; player model {int((~g['prospect']).sum()):4,}")

log("\nSTAR VALUE FOR A PLAYER STILL A PROSPECT ($M at the 2025-26 cap; through zero, no draft-year terms)")
log(f"  #1 pick: star chance {P1:.4f}. Left-out range: the star value with each draft left out in turn.")
for r in o.itertuples():
    log(f"  {r.seasons_since_draft:>2} seasons: star value {r.star_value_M:6.2f} (se {r.se_M:.2f}); #1 pick "
        f"{r.pick1_value_M:5.2f}; left-out range {r.lodo_min_M:.2f} to {r.lodo_max_M:.2f}; prospects {r.players:,} "
        f"({r.rows:,} rows); top-10 picks among them {r.top10_prospects}; with 1+ NHL game {r.share_with_nhl_games:.0%}")

o.to_csv(OUTPUT_DIR / "prospect_slot_years.csv", index=False)
d.to_csv(OUTPUT_DIR / "prospect_slot_years_rows.csv", index=False)
(OUTPUT_DIR / "prospect_slot_years_log.txt").write_text("\n".join(LOG), encoding="utf-8")
log(f"\nwrote prospect_slot_years.csv, prospect_slot_years_rows.csv, prospect_slot_years_log.txt in {OUTPUT_DIR}")
