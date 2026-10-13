"""
pick_star_gv_check.py -- does Bacon's star chance by slot hold up on a measure with no Bacon input?

WHY (meeting 2026-10-13; Thomas: "go ahead with the GV check"): the pick curve's shape is Bacon's
star probability by slot, fitted on his WAR over largely the same drafts whose surplus (also from his
WAR) sets the star value, so the agreement between the two is not independent. Game Value has no
Bacon input (built from our own game logs and expected-goals model). REPORT ONLY: it changes nothing.

WHAT GAME VALUE CAN AND CANNOT SHOW. Game Value covers 2017-18 to 2025-26 only, so it cannot price a
control window or a career; it can only say who is a star over those nine seasons. The check therefore
tests the SHAPE (how star rates fall with the slot), not the dollar star value.

THE STAR RULE, four ways, each over the same nine seasons (regular season), each requiring 200+ games
in the window (Bacon's NHLer bar), skaters only:
  bacon_war  WAR per 82 of 1.8+ (forwards) / 1.23+ (defencemen): Bacon's own thresholds, our window
  war_pct    top 20% of forwards / 15% of defencemen by WAR per 82, among ALL skaters with 200+ games
             in the window (Bacon describes his thresholds as about the top 20% / 15%)
  gv_adj     the same percentile rule on adjusted Game Value per 82 (gv_adjusted.csv `gv_adj`, the
             primary circularity validator since 2026-07-14)
  gv_raw     the same rule on raw Game Value per 82 (player_game_value.csv `game_value`; robustness)
war_pct against gv_adj changes ONLY the measure: same players, same window, same percentile rule.
bacon_war against Bacon's star chance shows what the nine-season window itself does.

THE DRAFTS: 2013-2019, declared before the run. The earliest class whose players had at most two or
three NHL seasons before 2017-18; the latest whose players have had six seasons to reach 200 games
(Bacon labels classes through 2021). Every selection enters the denominator, never-played included.
2010-2012 are printed beside as a coverage check only (their early seasons fall before the window).

THE READING, declared before the run: Game Value supports Bacon's shape if, in every pick range, the
gv_adj star rate is within two standard errors of the war_pct star rate on the same players (paired:
the standard error of the per-player difference). A range outside it is reported with its size. The
star rates against Bacon's mean star chance are reported, not judged (the window differs).

INPUTS: OUTPUT_DIR/draft_pick_linkage.csv, OUTPUT_DIR/gv_adjusted.csv, OUTPUT_DIR/player_game_value.csv,
SOURCE_DIR/skater_games.csv (games and positions by NHL id), SOURCE_DIR/WAR.csv,
SOURCE_DIR/draft_slot_baseline.csv.

Run from the repo root:  python 25_TESTS/pick_star_gv_check.py
"""

import os
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv

SCRIPT_VERSION = "pick_star_gv_check.py v1.0 (2026-10-13)"
print(SCRIPT_VERSION)
load_dotenv()
OUT, SRC = Path(os.environ["OUTPUT_DIR"]), Path(os.environ["SOURCE_DIR"])
F = {"linkage": OUT / "draft_pick_linkage.csv", "gv_adj": OUT / "gv_adjusted.csv",
     "gv_raw": OUT / "player_game_value.csv", "games": SRC / "skater_games.csv", "war": SRC / "WAR.csv",
     "bacon": SRC / "draft_slot_baseline.csv"}
for k, p in F.items():
    print(f"  input: {p.resolve()}  (modified {pd.Timestamp(p.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M})")

FIRST, LAST = 2017, 2025                     # window: start years of 2017-18 .. 2025-26
MIN_GP = 200                                 # Bacon's NHLer bar, applied inside the window
PCT = {"F": 0.20, "D": 0.15}                 # Bacon's description of his thresholds
BACON_T = {"F": 1.8, "D": 1.23}              # his thresholds, WAR per 82
MAIN, COVER = list(range(2013, 2020)), [2010, 2011, 2012]
RANGES = [(1, 1), (2, 3), (4, 10), (11, 20), (21, 32), (33, 64), (65, 128), (129, 300)]
MEASURES = ["bacon_war", "war_pct", "gv_adj", "gv_raw"]


def norm(s):
    """As draft_pick_linkage.norm / pick_curve.norm: strip accents, lowercase, letters and spaces."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z ]", "", s.lower()).strip()


# ---- Game Value per 82, by NHL id ------------------------------------------------------------------
g = pd.read_csv(F["games"], usecols=["game_id", "player_id", "position"], encoding="latin-1")   # names are not read; bytes vary
g = g[(g["game_id"] // 10000) % 100 == 2]                               # regular season (game type 02)
g["start"] = g["game_id"] // 1000000
g = g[g["start"].between(FIRST, LAST)]
gp = g.groupby(["player_id", "start"]).size().rename("GP")
pos_id = g.groupby("player_id")["position"].agg(lambda s: s.mode().iat[0]).map(lambda p: "D" if p == "D" else "F")

a = pd.read_csv(F["gv_adj"], usecols=["player_id", "season", "gv_adj"])
a["start"] = a["season"] // 10000
a = a[a["start"].between(FIRST, LAST)].join(gp, on=["player_id", "start"], how="inner")   # seasons in both
adj = a.groupby("player_id").agg(GP=("GP", "sum"), V=("gv_adj", "sum"))

r = pd.read_csv(F["gv_raw"], usecols=["game_id", "game_type", "player_id", "game_value"])
r = r[(r["game_type"] == 2) & ((r["game_id"] // 1000000).between(FIRST, LAST))]
raw = r.groupby("player_id").agg(GP=("game_value", "size"), V=("game_value", "sum"))

# ---- WAR per 82, by normalised name (as pick_curve.py matches WAR) ----------------------------------
w = pd.read_csv(F["war"], usecols=["Player", "Season", "Position", "GP", "WAR"])
w["start"] = w["Season"].map(lambda s: 2000 + int(str(s)[:2]))
w = w[w["start"].between(FIRST, LAST)]
w["name_n"] = w["Player"].map(norm)
war = w.groupby("name_n").agg(GP=("GP", "sum"), V=("WAR", "sum"),
                              pos=("Position", lambda s: s.mode().iat[0]))


def stars(tbl, pos, pct):
    """Per-82 rate for players with MIN_GP+ games; star = top PCT of his position among them."""
    t = tbl[tbl["GP"] >= MIN_GP].copy()
    t["rate"] = t["V"] / t["GP"] * 82
    t["pos"] = pos.reindex(t.index).values if pos is not None else t["pos"]
    t = t.dropna(subset=["pos"])
    cut = {p: t.loc[t["pos"] == p, "rate"].quantile(1 - pct[p]) for p in pct}
    t["star"] = t.apply(lambda x: x["rate"] >= cut[x["pos"]], axis=1)
    return t, cut


adj_t, adj_cut = stars(adj, pos_id, PCT)
raw_t, raw_cut = stars(raw, pos_id, PCT)
war_t, war_cut = stars(war, None, PCT)
print(f"\nwindow 2017-18 to 2025-26, {MIN_GP}+ games: skaters WAR {len(war_t):,}, GV-adj {len(adj_t):,}, "
      f"GV-raw {len(raw_t):,}")
print(f"  top-20%/15% cut, WAR per 82: F {war_cut['F']:.2f}, D {war_cut['D']:.2f}  "
      f"(Bacon's thresholds: F {BACON_T['F']}, D {BACON_T['D']})")
print(f"  cut, GV-adj per 82: F {adj_cut['F']:.2f}, D {adj_cut['D']:.2f}; GV-raw: F {raw_cut['F']:.2f}, D {raw_cut['D']:.2f}")

# ---- the picks --------------------------------------------------------------------------------------
link = pd.read_csv(F["linkage"])
link = link[link["draftYear"].isin(MAIN + COVER) & ~link["is_goalie"].astype(bool)
            & (link["link_status"] != "excluded_merged_name")].copy()
link["pos"] = np.where(link["position"] == "D", "D", "F")
bacon = pd.read_csv(F["bacon"])[["draft_pick", "p_star"]]
link = link.merge(bacon, left_on="overallPickNumber", right_on="draft_pick", how="left", validate="many_to_one")
assert link["p_star"].notna().all()


def war_row(row):
    """WAR games and total in the window for a drafted player, via the linkage's WAR names."""
    if pd.isna(row["war_names"]):
        return 0, 0.0
    names = {norm(x) for x in str(row["war_names"]).split("|")}
    s = w[w["name_n"].isin(names) & (w["start"] >= row["draftYear"])]   # GUARD: no namesake seasons before his draft
    return int(s["GP"].sum()), float(s["WAR"].sum())


wr = link.apply(war_row, axis=1, result_type="expand")
link["war_gp"], link["war_v"] = wr[0], wr[1]
link["war_rate"] = np.where(link["war_gp"] > 0, link["war_v"] / link["war_gp"].clip(lower=1) * 82, np.nan)
ok = link["war_gp"] >= MIN_GP
link["bacon_war"] = ok & (link["war_rate"] >= link["pos"].map(BACON_T))
link["war_pct"] = ok & (link["war_rate"] >= link["pos"].map(war_cut))
for m, t in (("gv_adj", adj_t), ("gv_raw", raw_t)):
    link[m] = link["playerId"].map(t["star"]).fillna(False).astype(bool)
link["gv_gp"] = link["playerId"].map(adj["GP"]).fillna(0)
for m in MEASURES:
    link[m] = link[m].astype(bool)


def table(d, label):
    print(f"\n{label}: {len(d):,} skater picks; star rates in % of ALL picks in the range (se)")
    print(f"  {'picks':>9} {'n':>5} {'Bacon':>7} | {'his rule':>12} {'WAR top%':>12} {'GV-adj':>12} {'GV-raw':>12} "
          f"| {'GV-adj minus WAR top% (paired se)':>34}")
    rows = []
    for lo, hi in RANGES + [(1, 300)]:
        s = d[d["overallPickNumber"].between(lo, hi)]
        n = len(s)
        cells = []
        for m in MEASURES:
            p = s[m].mean()
            cells.append(f"{100 * p:5.1f} ({100 * np.sqrt(p * (1 - p) / n):4.1f})")
        diff = s["gv_adj"].astype(float) - s["war_pct"].astype(float)
        dse = diff.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan
        within = abs(diff.mean()) <= 2 * dse if dse > 0 else diff.mean() == 0
        name = f"{lo}" if lo == hi else ("all" if (lo, hi) == (1, 300) else f"{lo}-{hi if hi < 300 else '+'}")
        print(f"  {name:>9} {n:5d} {100 * s['p_star'].mean():6.1f}% | " + " ".join(f"{c:>12}" for c in cells)
              + f" | {100 * diff.mean():+6.1f} ({100 * dse:4.1f})  {'within 2 se' if within else 'OUTSIDE 2 se'}")
        rows.append({"sample": label, "picks": name, "n": n, "bacon_p_star": s["p_star"].mean(),
                     **{m: s[m].mean() for m in MEASURES}, "gv_minus_war": diff.mean(), "paired_se": dse,
                     "within_2se": bool(within)})
    return rows


rows = table(link[link["draftYear"].isin(MAIN)], "MAIN, drafts 2013-2019")
main = link[link["draftYear"].isin(MAIN)]

# ---- agreement on who is a star, and slope on Bacon's star chance -----------------------------------
both = (main["war_pct"] & main["gv_adj"]).sum()
print(f"\nwho is a star (main drafts): WAR top% {int(main['war_pct'].sum())}, GV-adj {int(main['gv_adj'].sum())}, "
      f"both {int(both)}; of WAR stars, {100 * both / max(main['war_pct'].sum(), 1):.0f}% are GV-adj stars")
print("each star indicator regressed on Bacon's star chance, no constant, draft-year indicators summing to zero")
print("  (slope 1 = his chances are the right level for this rule; the shape test is the table above)")
yrs = main["draftYear"].values
cl = sorted(set(yrs))
Y = [(yrs == c).astype(float) - (yrs == cl[-1]).astype(float) for c in cl[:-1]]
for m in MEASURES:
    fit = sm.OLS(main[m].astype(float).values, np.column_stack([main["p_star"].values] + Y)).fit(cov_type="HC1")
    pr = sm.OLS(main[m].astype(float).values,
                np.column_stack([np.ones(len(main)), main["p_star"].values, np.log(main["overallPickNumber"].values)] + Y)
                ).fit(cov_type="HC1")
    print(f"  {m:9s} slope {fit.params[0]:.3f} (se {fit.bse[0]:.3f});  log(pick) added beside his chance: "
          f"{pr.params[2]:+.4f} (se {pr.bse[2]:.4f}, p {pr.pvalues[2]:.3f})")

# ---- coverage: older drafts, whose early seasons fall before the window -----------------------------
cov = link[link["draftYear"].isin(MAIN + COVER)].groupby("draftYear").agg(
    picks=("p_star", "size"), bacon=("p_star", "mean"), war_pct=("war_pct", "mean"), gv_adj=("gv_adj", "mean"),
    gv_200=("gv_gp", lambda s: (s >= MIN_GP).mean()))
print("\ncoverage by draft (rates as shares of all picks; gv_200 = share with 200+ Game Value games in the window)")
print(cov.round(3).to_string())

verdict = all(r["within_2se"] for r in rows)
print(f"\nREADING (declared): GV-adj within two paired standard errors of the WAR percentile rule in every range: "
      f"{'YES' if verdict else 'NO'} ({sum(r['within_2se'] for r in rows)} of {len(rows)} rows, 'all' row included)")
pd.DataFrame(rows).to_csv(OUT / "pick_star_gv_check.csv", index=False)
link.to_csv(OUT / "pick_star_gv_check_players.csv", index=False)
print(f"wrote pick_star_gv_check.csv, pick_star_gv_check_players.csv in {OUT}")
