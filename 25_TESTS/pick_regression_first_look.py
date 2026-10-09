"""
pick_regression_first_look.py -- the first look at the draft pick regression.

WHAT THIS IS (MODEL_DIRECTIVES.md directive 6, 2026-10-09)
-------------------------------------------------------------------
A FIRST LOOK, not a locked curve and not the declared tests. It prices each
drafted skater's seasons in dollars, sums them over his control window, and
regresses that total on draft slot, as decided on 2026-10-09:
  * one regression on slot across all picks, with and without draft-year
    indicators (a pick is valued at the average draft year);
  * each player priced first, then the dollars regressed (Thomas);
  * the WAR-on-slot regression reported beside it;
  * a straight line in pick number AND log(pick), shown side by side. Which
    form wins is one of the declared tests (left-out classes), not decided here.
Skaters only: goalies are a declared test (with skaters, separate, left out;
Thomas's first guess, skaters only).

ONE PLAYER'S DOLLARS, STEP BY STEP
-------------------------------------------------------------------
For every skater picked in the 2007-2017 classes (every selection; a player
who never plays is a real zero):
 1. WINDOW: seasons from his draft year to the end of the qualifying-offer
    chain, from `draft_window_count.csv` (CBA Group 3: 27 as of June 30, or
    seven Accrued Seasons; Group 6 NOT applied). Cut at 2025-26; the 2017
    class's 29 short windows stay as they are (Thomas, 2026-10-09).
 2. A SEASON WITH NO NHL GAME is worth zero and costs zero (Thomas).
 3. VALUE of a season he played: the delivered-win price on the contract line
    (open decision 3): max(alpha + beta x WAR + gamma_term x 1, league
    minimum), in cap share of that season, with beta by position (defence
    slope for D). Term = 1: entry-level and control seasons are priced as
    one-year deals (Thomas). Constants: skater_forward_projection.
    price_constants() (XNPV1_RATE, term-in).
 4. SHORT SEASONS: WAR in 2012-13, 2019-20 and 2020-21 is scaled to 82 games
    (x82/48, x82/70, x82/56) before pricing. D20 locks 82/70 and 82/56;
    82/48 extends it to 2012-13 (flagged; carried from the archived curve).
    Costs are not scaled (cap shares are already annual ratios).
 5. COST:
    * Entry-level seasons: the entry-level maximum for his draft class, as a
      share of the season's cap. Which seasons: every season up to and
      including his Nth season with 10+ NHL games, N from CBA 9.1(b) by his
      age on September 15 of his first NHL season (3 if 18-21, 2 if 22-23,
      1 if 24 or older). PROXIES: his signing age and date are not observed
      (first NHL season stands in), and seasons under 10 games do not use up
      the deal, like the 9.1(d) slide. Slides are a declared test.
    * After it: a chain of one-year qualifying offers
      (rfa_terminal_value.qualifying_offer, era bands, floored at the league
      minimum), the first on the entry-level maximum as the prior salary,
      each next one on the previous offer. The chain advances every season
      after the entry-level deal; a season with no NHL game still costs zero.
 6. PARTIAL SEASONS (a DECISION FOR THOMAS, both shown): "full" prices any
    season with an NHL game as a full season (value floor and cost in full);
    "cameo" scales the season's priced value and its cost by games/82 when
    he played under 10 games (adapted from the archived curve, which scaled
    the floor and the cost: the term-in line's intercept plus one year of
    term is itself about $0.43M, so scaling the floor alone would still
    credit a 3-game callup with most of a season).
 7. SUM the season surpluses in cap share and express them at the 2025-26
    ceiling ($95.5M). Summing cap shares is the player model's convention:
    3% cap growth and 3% discounting cancel (D11).

TRAILING WEIGHTING CHECK (directive 6): nothing here reads a trailing total.
Each season is priced on the WAR delivered that season. price_constants(),
qualifying_offer() and league_min_path() read no player seasons.

INPUTS (paths from .env): OUTPUT_DIR/draft_pick_linkage.csv,
OUTPUT_DIR/draft_window_count.csv (25_TESTS/draft_window_count.py), SOURCE_DIR/
WAR.csv. CONSTANTS for 2007-2014 caps and league minimums and the entry-level
maxima by class: public CBA figures carried from the archived draft curve
(90_ARCHIVE/2026-10-09/draft_yield_curve.py, verified 2026-07-14); from
2015 on the live tables are used and the two are asserted equal.

OUTPUTS: OUTPUT_DIR/pick_first_look_players.csv (one row per pick),
OUTPUT_DIR/pick_first_look_curve.csv (fitted values by pick),
OUTPUT_DIR/pick_first_look_log.txt.

Run from the repo root:  python 25_TESTS/pick_regression_first_look.py
"""

import os
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from dotenv import load_dotenv

SCRIPT_VERSION = "pick_regression_first_look.py v1.0 (2026-10-09)"

load_dotenv()
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
import skater_forward_projection as sfp          # noqa: E402  price line, cap and minimum tables
import rfa_terminal_value as rtv                 # noqa: E402  qualifying-offer formula

SOURCE_DIR = Path(os.environ["SOURCE_DIR"])
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


log(SCRIPT_VERSION)
INPUTS = {"linkage": OUTPUT_DIR / "draft_pick_linkage.csv",
          "windows": OUTPUT_DIR / "draft_window_count.csv",
          "WAR": SOURCE_DIR / "WAR.csv"}
for k, p in INPUTS.items():
    log(f"  input {k}: {p.resolve()}  (modified {pd.Timestamp(p.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M})")

# ---- constants -----------------------------------------------------------
ALPHA, BETA_F, BETA_D, GAMMA, LINE = sfp.price_constants()
TERM = 1                                          # every drafted season priced as a one-year deal
log(f"  price line: {LINE}: alpha {ALPHA:.10f}, beta F {BETA_F:.10f}, D {BETA_D:.10f}, term {GAMMA:.10f}")

# Caps and league minimums by season START year. 2007-2014 carried from the
# archived curve (public CBA figures); 2015+ must equal the live tables.
CAP_OLD = {2007: 50.3e6, 2008: 56.7e6, 2009: 56.8e6, 2010: 59.4e6, 2011: 64.3e6,
           2012: 60.0e6, 2013: 64.3e6, 2014: 69.0e6, 2015: 71.4e6, 2016: 73.0e6,
           2017: 75.0e6, 2018: 79.5e6, 2019: 81.5e6, 2020: 81.5e6, 2021: 81.5e6,
           2022: 82.5e6, 2023: 83.5e6, 2024: 88.0e6, 2025: 95.5e6}
MIN_OLD = {2007: 475_000, 2008: 475_000, 2009: 500_000, 2010: 500_000, 2011: 525_000,
           2012: 525_000, 2013: 550_000, 2014: 550_000, 2015: 575_000, 2016: 575_000,
           2017: 650_000, 2018: 650_000, 2019: 700_000, 2020: 700_000, 2021: 750_000,
           2022: 750_000, 2023: 775_000, 2024: 775_000, 2025: 775_000}
for y in range(2015, 2026):                       # GUARD: carried figures agree with the live tables
    assert CAP_OLD[y] == sfp.CAP_CEILING[y], y
    assert MIN_OLD[y] == sfp.league_min_path(y), y
CAP = lambda y: CAP_OLD[y]
LEAGUE_MIN = lambda y: MIN_OLD[y]
CAP_NOW = sfp.CAP_CEILING[2025]                   # dollars are stated at the 2025-26 ceiling

ELC_MAX = {**{y: 875_000 for y in (2007, 2008)}, **{y: 900_000 for y in (2009, 2010)},
           **{y: 925_000 for y in range(2011, 2018)}}   # by DRAFT year (class maximum)
SHORT = {2012: 82 / 48, 2019: 82 / 70, 2020: 82 / 56}   # WAR scaled to 82 games, by start year
CAMEO_GP = 10                                     # under 10 games: a cameo (cameo arm; the ELC count)
LAST_START = 2025                                 # 2025-26 is the last season in the data


def norm(s):
    """draft_pick_linkage.norm: strip accents, lowercase, letters and spaces."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z ]", "", s.lower()).strip()


def elc_years(age):
    """CBA 9.1(b): first-contract signing age -> years in the entry-level system (25+ treated as 1)."""
    return 3 if age <= 21 else 2 if age <= 23 else 1


# ---- the picks -------------------------------------------------------------
link = pd.read_csv(INPUTS["linkage"], parse_dates=["birthDate"])
win = pd.read_csv(INPUTS["windows"])
picks = link[link["draftYear"].between(2007, 2017)].merge(
    win[["draftYear", "overall", "end_g3"]], left_on=["draftYear", "overallPickNumber"],
    right_on=["draftYear", "overall"], how="left", validate="one_to_one")
n_all = len(picks)
picks = picks[~picks["is_goalie"].astype(bool)]
log(f"\npicks 2007-2017: {n_all:,}; skaters {len(picks):,} (goalies left out of this first look)")
drop = picks["end_g3"].isna() | (picks["link_status"] == "excluded_merged_name")
log(f"  without a window (forfeits, merged-name exclusion): {drop.sum()}: "
    + "; ".join(f"{r.draftYear} #{r.overallPickNumber} {r.playerName}" for r in picks[drop].itertuples()))
picks = picks[~drop].copy()

# ---- season WAR and games, summed over team rows, from the draft on --------
war = pd.read_csv(INPUTS["WAR"], usecols=["Player", "Season", "GP", "WAR"])
war["name_n"] = war["Player"].map(norm)
war["start"] = war["Season"].map(lambda s: 2000 + int(str(s)[:2]))
war = war.groupby(["name_n", "start"])[["GP", "WAR"]].sum()


def seasons_of(row):
    if pd.isna(row["war_names"]):
        return pd.DataFrame(columns=["GP", "WAR"])
    parts = [war.loc[n] for n in {norm(x) for x in str(row["war_names"]).split("|")}
             if n in war.index.get_level_values(0)]
    if not parts:
        return pd.DataFrame(columns=["GP", "WAR"])
    s = pd.concat(parts).groupby(level=0).sum()
    return s[s.index >= row["draftYear"]]           # GUARD: a namesake's earlier seasons cannot leak in


def price_player(row, arm):
    """Sum of season surpluses (cap shares) over his window; also WAR and NHL seasons."""
    s = seasons_of(row)
    beta = BETA_D if row["position"] == "D" else BETA_F
    last = min(int(row["end_g3"]) - 1, LAST_START)  # end_g3 is the end-year of the last controlled season
    played = s[(s["GP"] > 0) & (s.index <= last)]
    if played.empty:
        return 0.0, 0.0, 0.0, 0.0, 0
    first = int(played.index.min())
    age = (pd.Timestamp(first, 9, 15) - row["birthDate"]).days / 365.25 if pd.notna(row["birthDate"]) else 19
    n_elc, elc_done, prior, v_tot, c_tot, w_tot = elc_years(int(age)), 0, None, 0.0, 0.0, 0.0
    for y in range(int(row["draftYear"]), last + 1):
        gp = float(s.loc[y, "GP"]) if y in s.index else 0.0
        wins = float(s.loc[y, "WAR"]) * SHORT.get(y, 1.0) if y in s.index else 0.0
        in_elc = elc_done < n_elc and gp > 0
        if not in_elc and elc_done >= n_elc:         # qualifying-offer chain: advances every season after the deal
            prior = rtv.qualifying_offer(prior or ELC_MAX[row["draftYear"]], prior or ELC_MAX[row["draftYear"]],
                                         y, False)
        if gp == 0:
            continue                                  # no NHL game: worth zero, costs zero
        cap = CAP(y)
        scale = gp / 82 if (arm == "cameo" and gp < CAMEO_GP) else 1.0
        floor = LEAGUE_MIN(y) / cap
        value = max(ALPHA + beta * wins + GAMMA * TERM, floor) * scale   # cameo arm: a few games, a few games' worth
        cost = (ELC_MAX[row["draftYear"]] if in_elc else prior) / cap * scale
        v_tot, c_tot, w_tot = v_tot + value, c_tot + cost, w_tot + wins
        if in_elc and gp >= CAMEO_GP:
            elc_done += 1                             # a 10+ game season uses up an entry-level year
    return v_tot - c_tot, v_tot, c_tot, w_tot, len(played)


for arm in ("full", "cameo"):
    out = picks.apply(lambda r: price_player(r, arm), axis=1, result_type="expand")
    picks[f"surplus_{arm}"] = out[0] * CAP_NOW
    if arm == "full":
        picks["value"], picks["cost"], picks["war"], picks["nhl_seasons"] = (
            out[1] * CAP_NOW, out[2] * CAP_NOW, out[3], out[4])
picks["pick"] = picks["overallPickNumber"]
picks["log_pick"] = np.log(picks["pick"])
picks["cls"] = picks["draftYear"].astype(str)
picks["played"] = picks["nhl_seasons"] > 0

# ---- what the outcomes look like ------------------------------------------
log(f"\nskater picks priced: {len(picks):,}; played an NHL game: {picks['played'].sum():,}")
log(f"surplus per pick ($M at the 2025-26 cap), 'full' arm: mean {picks['surplus_full'].mean()/1e6:.2f}, "
    f"median {picks['surplus_full'].median()/1e6:.2f}, max {picks['surplus_full'].max()/1e6:.1f}")
log(f"'cameo' arm mean {picks['surplus_full'].mean()/1e6:.3f} -> {picks['surplus_cameo'].mean()/1e6:.3f}; "
    f"picks that differ: {(picks['surplus_full'] - picks['surplus_cameo']).abs().gt(1).sum()}")
bands = [(1, 1), (2, 2), (3, 5), (6, 10), (11, 20), (21, 32), (33, 64), (65, 100), (101, 150), (151, 217)]
rows = []
for lo, hi in bands:
    d = picks[picks["pick"].between(lo, hi)]
    rows.append({"picks": f"{lo}-{hi}", "n": len(d), "played_%": 100 * d["played"].mean(),
                 "mean_$M": d["surplus_full"].mean() / 1e6, "median_$M": d["surplus_full"].median() / 1e6,
                 "mean_WAR": d["war"].mean(), "mean_value_$M": d["value"].mean() / 1e6,
                 "mean_cost_$M": d["cost"].mean() / 1e6})
log("\nRAW AVERAGES BY PICK RANGE (display only; the regression uses every pick), 'full' arm")
log(pd.DataFrame(rows).round(2).to_string(index=False))
top = picks.nlargest(10, "surplus_full")[["draftYear", "pick", "playerName", "war", "surplus_full"]]
log("\nlargest surpluses ($M):")
log(top.assign(surplus_full=top["surplus_full"] / 1e6).round(2).to_string(index=False))
low = picks.nsmallest(5, "surplus_full")[["draftYear", "pick", "playerName", "war", "surplus_full"]]
log("smallest:")
log(low.assign(surplus_full=low["surplus_full"] / 1e6).round(2).to_string(index=False))

# ---- the regressions ---------------------------------------------------------
# Robust (HC1) standard errors: outcomes are very uneven across picks.
# With draft-year indicators the prediction is at the AVERAGE draft year:
# the class effects are averaged with equal weight (sum-to-zero coding).
specs = {
    "$ on pick":                 ("surplus_full ~ pick", False),
    "$ on log(pick)":            ("surplus_full ~ log_pick", False),
    "$ on pick + year":          ("surplus_full ~ pick + C(cls, Sum)", True),
    "$ on log(pick) + year":     ("surplus_full ~ log_pick + C(cls, Sum)", True),
    "WAR on pick + year":        ("war ~ pick + C(cls, Sum)", True),
    "WAR on log(pick) + year":   ("war ~ log_pick + C(cls, Sum)", True),
}
grid = pd.DataFrame({"pick": np.arange(1, 218)})
grid["log_pick"] = np.log(grid["pick"])
log("\nREGRESSIONS (skaters, 2007-2017, n = %d)" % len(picks))
fits = {}
for name, (f, has_year) in specs.items():
    m = smf.ols(f, data=picks).fit(cov_type="HC1")
    fits[name] = m
    slope_name = "log_pick" if "log_pick" in f else "pick"
    # Prediction at the average year: with Sum coding the intercept IS the average-year level.
    pred = m.params["Intercept"] + m.params[slope_name] * grid[slope_name]
    grid[name] = pred
    unit = 1e6 if f.startswith("surplus") else 1.0
    log(f"  {name:24s} slope {m.params[slope_name]/unit:+.4f} (se {m.bse[slope_name]/unit:.4f})"
        f"{' $M' if unit == 1e6 else ' WAR'}  R2 {m.rsquared:.3f}  adj {m.rsquared_adj:.3f}")
    if has_year:
        yr = m.params.filter(like="C(cls").values / unit
        yr = np.append(yr, -yr.sum())                # the omitted class under sum-to-zero coding
        log(f"  {'':24s} draft-year effects (2007..2017), spread {yr.min():+.2f} to {yr.max():+.2f}")

at = [1, 2, 3, 5, 10, 15, 20, 32, 64, 100, 150, 200]
log("\nFITTED SURPLUS AT AN AVERAGE DRAFT YEAR ($M, 2025-26 cap); raw mean of that exact pick beside it")
tbl = grid.set_index("pick").loc[at, [k for k in specs if k.startswith("$")]] / 1e6
tbl["raw mean at pick"] = [picks.loc[picks["pick"] == p, "surplus_full"].mean() / 1e6 for p in at]
tbl["picks at slot"] = [int((picks["pick"] == p).sum()) for p in at]
log(tbl.round(2).to_string())
log("\nFITTED WAR OVER THE WINDOW AT AN AVERAGE DRAFT YEAR")
log(grid.set_index("pick").loc[at, ["WAR on pick + year", "WAR on log(pick) + year"]].round(2).to_string())

# ---- outputs ---------------------------------------------------------------------
cols = ["draftYear", "pick", "roundNumber", "playerName", "position", "link_status", "end_g3",
        "nhl_seasons", "war", "value", "cost", "surplus_full", "surplus_cameo"]
picks[cols].to_csv(OUTPUT_DIR / "pick_first_look_players.csv", index=False)
grid.to_csv(OUTPUT_DIR / "pick_first_look_curve.csv", index=False)
(OUTPUT_DIR / "pick_first_look_log.txt").write_text("\n".join(LOG), encoding="utf-8")
log(f"\nwrote pick_first_look_players.csv, pick_first_look_curve.csv, pick_first_look_log.txt in {OUTPUT_DIR}")
