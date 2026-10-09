"""
pick_curve.py -- the draft pick curve: what a pick is worth, in the player model's dollars.

SPECIFICATION: 00_STATE/MODEL_DIRECTIVES.md directive 6, decided with Thomas on
2026-10-09 step by step (tests and checks in 25_TESTS/pick_*.py). Every rule below
is a recorded decision; the label in brackets says where it was decided or tested.

A PICK'S VALUE
  value = SCALE x Bacon's star chance for the slot              [adopted 2026-10-09]
  * Star chance: SOURCE_DIR/draft_slot_baseline.csv `p_star` (Bacon; a star has
    career WAR per 82 games of 1.8+ forwards / 1.23+ defencemen; his slot
    baseline is a logistic regression on pick number with a kink at pick 150).
    The shape across picks is his; this script fits only the dollar SCALE.
  * SCALE: each drafted player's surplus regressed on the star chance of his
    slot, through zero, with draft-year indicators that sum to zero, so the
    scale is the average draft year's [pick_star_form_test.py: through zero won].
  * Two scales are written:                                 [pick_lookahead_check.py]
      knowable  for trade season T, fitted only on classes drafted T-9 or
                earlier (their control windows had largely run out): the MAIN
                scale, so a pick is priced with what a club could know;
      pooled    fitted on every class 2007-2017: the SENSITIVITY.

ONE DRAFTED PLAYER'S SURPLUS (classes 2007-2017, every selection, all positions)
  1. WINDOW: from the draft to the end of club control under CBA Group 3
     (Section 10.1(a)): 27 as of June 30, or seven Accrued Seasons (Article 1:
     40 active-roster games, 30 for a goalie; NHL games played stand in for
     roster games; 2012-13 pro-rated 48/82 by the CBA, 2019-20 and 2020-21
     pro-rated 70/82 and 56/82 as an assumption). Cut at 2025-26.
                                                     [draft_window_count.py]
  2. A SEASON WITH NO NHL GAME is worth zero and costs zero.
  3. VALUE of a season played: the delivered-win price on the contract line,
     max(alpha + beta x WAR + gamma_term x 1, league minimum) as a share of
     that season's cap (skaters: skater_forward_projection.price_constants(),
     XNPV1_RATE, defence slope for D, every season priced as a one-year deal);
     goalies: max(alpha_G + beta_G x WAR, league minimum) on the goalie line
     (contract_npv, recovered from the goalie spine; no term).
  4. SHORT SEASONS: WAR in 2012-13, 2019-20, 2020-21 scaled to 82 games
     (82/48, 82/70, 82/56) [D20; 82/48 decided 2026-10-09].
  5. PARTIAL SEASONS: under 10 NHL games, the season's value and cost are
     scaled by games/82 [decided 2026-10-09].
  6. COST: the entry-level maximum for his draft class while his entry-level
     deal runs, then a chain of one-year qualifying offers
     (rfa_terminal_value.qualifying_offer; first on the entry-level maximum,
     each next on the previous offer). The entry-level deal runs by CALENDAR
     from his first NHL season, NO SLIDES [decided 2026-10-09], for 3 / 2 / 1
     seasons by his age on September 15 of that season (CBA 9.1(b): 18-21 /
     22-23 / 24+; 25+ treated as 1).
  7. SUM the seasons' surplus in cap shares and state it at the 2025-26
     ceiling (3% cap growth and 3% discounting cancel, D11). A NEGATIVE total
     counts as negative [decided 2026-10-09].
  8. RIGHTS THAT LAPSED: a player whose first NHL season was for another club,
     with no trade of him between his draft and the end of that season in
     trades.db, and the earlier pick of a player drafted twice, are worth ZERO
     to the pick [decided 2026-10-09; pick_star_and_rights_checks.py v1.1].
  9. GOALIES are pooled with skaters in one scale [decided 2026-10-09].

TRAILING WEIGHTING CHECK (directive 6): nothing here reads a trailing total.

INPUTS (paths from .env): OUTPUT_DIR/draft_pick_linkage.csv (draft_pick_linkage.py),
SOURCE_DIR/WAR.csv, Goalies_WAR.csv, draft_slot_baseline.csv, trades.db.
OUTPUTS: OUTPUT_DIR/pick_curve_players.csv (one row per pick), OUTPUT_DIR/pick_curve_seasons.csv
(v1.1: one row per priced season, the audit trail behind each pick's total; no result changes),
OUTPUT_DIR/pick_curve_scales.csv (the scales), OUTPUT_DIR/pick_curve_log.txt.

Run from the repo root:  python 20_CODE/pick_curve.py
"""

import os
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv

SCRIPT_VERSION = "pick_curve.py v1.1 (2026-10-09)"
load_dotenv()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import skater_forward_projection as sfp          # noqa: E402  skater price line, cap and minimum tables
import rfa_terminal_value as rtv                 # noqa: E402  qualifying-offer formula
import contract_npv as cnpv                      # noqa: E402  goalie price line (recovered on import)

SOURCE_DIR, OUTPUT_DIR = Path(os.environ["SOURCE_DIR"]), Path(os.environ["OUTPUT_DIR"])
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


log(SCRIPT_VERSION)
F = {"linkage": OUTPUT_DIR / "draft_pick_linkage.csv", "WAR": SOURCE_DIR / "WAR.csv",
     "GWAR": SOURCE_DIR / "Goalies_WAR.csv", "bacon": SOURCE_DIR / "draft_slot_baseline.csv",
     "trades": SOURCE_DIR / "trades.db"}
for k, p in F.items():
    log(f"  input {k}: {p.resolve()}  (modified {pd.Timestamp(p.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M})")

# ---- constants ------------------------------------------------------------------------------
CLASSES = range(2007, 2018)
LAST_START = 2025                                  # 2025-26, the last season in the data (start year)
ALPHA, BETA_F, BETA_D, GAMMA, LINE = sfp.price_constants()
ALPHA_G, BETA_G = cnpv.ALPHA_G, cnpv.BETA_G
log(f"  skater line: {LINE} alpha {ALPHA:.10f} beta F {BETA_F:.10f} D {BETA_D:.10f} term {GAMMA:.10f}")
log(f"  goalie line: alpha {ALPHA_G:.10f} beta {BETA_G:.10f}")
# Caps and league minimums by season START year: 2007-2014 public CBA figures carried
# from the archived curve (90_ARCHIVE/2026-10-09/draft_yield_curve.py, verified 2026-07-14);
# 2015 on, the live tables.
CAP = {2007: 50.3e6, 2008: 56.7e6, 2009: 56.8e6, 2010: 59.4e6, 2011: 64.3e6, 2012: 60.0e6, 2013: 64.3e6,
       2014: 69.0e6, **{y: sfp.CAP_CEILING[y] for y in range(2015, 2026)}}
LMIN = {2007: 475_000, 2008: 475_000, 2009: 500_000, 2010: 500_000, 2011: 525_000, 2012: 525_000,
        2013: 550_000, 2014: 550_000, **{y: sfp.league_min_path(y) for y in range(2015, 2026)}}
ELC_MAX = {**{y: 875_000 for y in (2007, 2008)}, **{y: 900_000 for y in (2009, 2010)},
           **{y: 925_000 for y in range(2011, 2018)}}   # by DRAFT year
SHORT = {2012: 82 / 48, 2019: 82 / 70, 2020: 82 / 56}  # WAR to 82 games, by start year
ACCRUE_PRORATE = {2012: 48 / 82, 2019: 70 / 82, 2020: 56 / 82}   # Accrued Season thresholds, by start year
CAP_NOW, CAMEO_GP = sfp.CAP_CEILING[2025], 10
FRANCHISE = {"N.J": "NJD", "S.J": "SJS", "T.B": "TBL", "L.A": "LAK", "ATL": "WPG", "PHX": "ARI", "UTA": "ARI"}
SHORT_FORMS = {"tony": "anthony", "josh": "joshua", "mike": "michael", "alex": "alexander", "matt": "matthew",
               "nick": "nicholas", "will": "william", "zach": "zachary", "jake": "jacob", "dan": "daniel",
               "danny": "daniel", "chris": "christopher", "sam": "samuel", "ben": "benjamin", "tom": "thomas",
               "jon": "jonathan", "joe": "joseph", "andy": "andrew", "nate": "nathan", "max": "maxim",
               "steve": "steven", "rob": "robert", "bobby": "robert"}


def norm(s):
    """draft_pick_linkage.norm: strip accents, lowercase, letters and spaces."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z ]", "", s.lower()).strip()


def name_key(s):
    parts = norm(s).split()
    return (parts[-1], SHORT_FORMS.get(parts[0], parts[0])) if len(parts) > 1 else (norm(s), "")


def year_reaching(birth, age):
    """Start year of the last season at whose June 30 he is younger than `age`, plus one: i.e. the
    END-year of the first League Year at whose June 30 he is `age` or older."""
    return birth.year + age + (1 if (birth.month, birth.day) > (6, 30) else 0)


# ---- the picks and their NHL seasons ---------------------------------------------------------
link = pd.read_csv(F["linkage"], parse_dates=["birthDate"])
picks = link[link["draftYear"].isin(CLASSES)].copy()
picks["is_goalie"] = picks["is_goalie"].astype(bool)
drop = (picks["link_status"] == "excluded_merged_name") | picks["birthDate"].isna()
log(f"\npicks 2007-2017: {len(picks):,}; set aside (merged-name exclusion or no birthdate): {int(drop.sum())}: "
    + "; ".join(f"{r.draftYear} #{r.overallPickNumber} {r.playerName}" for r in picks[drop].itertuples()))
picks = picks[~drop].copy()


def season_table(path, name_col):
    w = pd.read_csv(path, usecols=[name_col, "Season", "Team", "GP", "WAR"])
    w["name_n"] = w[name_col].map(norm)
    w["start"] = w["Season"].map(lambda s: 2000 + int(str(s)[:2]))
    w["teams"] = w["Team"].astype(str).map(lambda t: {FRANCHISE.get(x, x) for x in t.split("/")})
    g = w.groupby(["name_n", "start"]).agg(GP=("GP", "sum"), WAR=("WAR", "sum"),
                                           teams=("teams", lambda s: set().union(*s)))
    return g


TABLES = {False: season_table(F["WAR"], "Player"), True: season_table(F["GWAR"], "Goalie")}


def seasons_of(row):
    tbl = TABLES[row["is_goalie"]]
    if pd.isna(row["war_names"]):
        return tbl.iloc[0:0]
    names = {norm(x) for x in str(row["war_names"]).split("|")} & set(tbl.index.get_level_values(0))
    if not names:
        return tbl.iloc[0:0]
    s = pd.concat([tbl.loc[n] for n in names])
    s = s.groupby(level=0).agg({"GP": "sum", "WAR": "sum", "teams": lambda x: set().union(*x)})
    return s[s.index >= row["draftYear"]]           # GUARD: a namesake's earlier seasons cannot leak in


def window_end(row, s):
    """END-year of his last controlled season (CBA Group 3)."""
    base = 30 if row["is_goalie"] else 40
    accrued = sorted(y + 1 for y, g in s["GP"].items() if g >= base * ACCRUE_PRORATE.get(y, 1.0))
    a7 = accrued[6] if len(accrued) >= 7 else None
    y27 = year_reaching(row["birthDate"], 27)
    return min(y27, a7) if a7 else y27


SEASONS = []


def price(row, s, last):
    """Summed surplus (cap shares) over the window, under the decided rules."""
    played = s[(s["GP"] > 0) & (s.index <= last)]
    if played.empty:
        return 0.0, 0.0, 0
    first = int(played.index.min())
    age = int((pd.Timestamp(first, 9, 15) - row["birthDate"]).days / 365.25)
    n_elc = 3 if age <= 21 else 2 if age <= 23 else 1
    beta = BETA_D if row["position"] == "D" else BETA_F
    prior, tot, war_tot = None, 0.0, 0.0
    for y in range(int(row["draftYear"]), last + 1):
        in_elc = first <= y < first + n_elc          # by calendar from his first NHL season: no slides
        if y >= first + n_elc:
            prior = rtv.qualifying_offer(prior or ELC_MAX[row["draftYear"]], prior or ELC_MAX[row["draftYear"]],
                                         y, False)
        gp = float(s.loc[y, "GP"]) if y in s.index else 0.0
        if gp == 0:
            continue                                 # no NHL game: worth zero, costs zero
        wins = float(s.loc[y, "WAR"]) * SHORT.get(y, 1.0)
        floor = LMIN[y] / CAP[y]
        raw = (ALPHA_G + BETA_G * wins) if row["is_goalie"] else (ALPHA + beta * wins + GAMMA * 1)
        scale = gp / 82 if gp < CAMEO_GP else 1.0
        value = max(raw, floor) * scale
        cost = (ELC_MAX[row["draftYear"]] if in_elc else prior) / CAP[y] * scale
        tot += value - cost
        war_tot += wins
        SEASONS.append({"draftYear": row["draftYear"], "pick": row["overallPickNumber"], "season": y,
                        "gp": gp, "war_82": wins, "in_entry_level": in_elc, "games_scale": scale,
                        "cap": CAP[y], "value_share": value, "cost_share": cost,
                        "cost_$": (ELC_MAX[row["draftYear"]] if in_elc else prior) * scale})
    return tot, war_tot, len(played)


# ---- rights that lapsed -------------------------------------------------------------------------
con = sqlite3.connect(F["trades"])
ta = pd.read_sql("select a.player_name, t.trade_date from trade_assets a join trades t using(trade_id) "
                 "where a.asset_type = 'player'", con)
ta["key"], ta["date"] = ta["player_name"].map(name_key), pd.to_datetime(ta["trade_date"])
twice = link.dropna(subset=["playerId"]).groupby("playerId")["draftYear"].agg(["nunique", "max"])
twice = twice[twice["nunique"] > 1]


def route(row, s):
    played = s[s["GP"] > 0]
    if played.empty:
        return "never played"
    if pd.notna(row["playerId"]) and row["playerId"] in twice.index and row["draftYear"] < twice.loc[row["playerId"], "max"]:
        return "drafted twice (earlier pick)"
    first = int(played.index.min())
    if FRANCHISE.get(row["triCode"], row["triCode"]) in played.loc[first, "teams"]:
        return "same team"
    after, ends = pd.Timestamp(int(row["draftYear"]), 6, 1), pd.Timestamp(first + 1, 7, 1)
    if ((ta["key"] == name_key(row["playerName"])) & (ta["date"] > after) & (ta["date"] < ends)).any():
        return "traded first"
    return "lapsed"


rows = []
for r in picks.itertuples():
    row = r._asdict()
    s = seasons_of(row)
    end = window_end(row, s)
    last = min(end - 1, LAST_START)
    sur, wins, n = price(row, s, last)
    rt = route(row, s)
    rows.append({"draftYear": r.draftYear, "pick": r.overallPickNumber, "round": r.roundNumber, "player": r.playerName,
                 "playerId": r.playerId, "position": r.position, "is_goalie": r.is_goalie, "team": r.triCode,
                 "window_end": end, "nhl_seasons": n, "war": wins, "route": rt,
                 "surplus_before_rights": sur * CAP_NOW,
                 "surplus": 0.0 if rt in ("lapsed", "drafted twice (earlier pick)") else sur * CAP_NOW})
d = pd.DataFrame(rows)
bacon = pd.read_csv(F["bacon"]).set_index("draft_pick")["p_star"]
d["p_star"] = d["pick"].map(bacon)
assert d["p_star"].notna().all()

# ---- guards against the tests that decided each step (when their outputs are on this machine) ----
wc = OUTPUT_DIR / "draft_window_count.csv"
if wc.exists():
    w = pd.read_csv(wc)[["draftYear", "overall", "end_g3"]].rename(columns={"overall": "pick"})
    m = d.merge(w, on=["draftYear", "pick"], how="inner")
    log(f"  guard, window ends vs draft_window_count.csv: {int((m['window_end'] == m['end_g3']).sum())} of {len(m)} equal")
    assert (m["window_end"] == m["end_g3"]).all()
ct = OUTPUT_DIR / "pick_cost_and_year_tests.csv"
if ct.exists():
    t = pd.read_csv(ct)[["draftYear", "overallPickNumber", "no_slides"]].rename(columns={"overallPickNumber": "pick"})
    m = d.merge(t, on=["draftYear", "pick"], how="inner")
    gap = (m["surplus_before_rights"] / 1e6 - m["no_slides"]).abs()
    log(f"  guard, skater surplus vs pick_cost_and_year_tests no_slides: {int((gap < 1e-6).sum())} of {len(m)} equal")
    assert (gap < 1e-6).all()

log(f"\npicks priced: {len(d):,} ({int(d['is_goalie'].sum())} goalies); played an NHL game: "
    f"{int((d['nhl_seasons'] > 0).sum()):,}")
log("routes: " + ", ".join(f"{k} {v}" for k, v in d["route"].value_counts().items()))
log(f"surplus zeroed for lapsed rights: ${d.loc[d['surplus'] != d['surplus_before_rights'], 'surplus_before_rights'].sum() / 1e6:,.1f}M "
    f"of ${d['surplus_before_rights'].sum() / 1e6:,.1f}M")

# ---- the scales ------------------------------------------------------------------------------------
def fit_scale(frame):
    cl = sorted(frame["draftYear"].unique())
    yrs = frame["draftYear"].values
    X = [frame["p_star"].values] + [(yrs == c).astype(float) - (yrs == cl[-1]).astype(float) for c in cl[:-1]]
    m = sm.OLS(frame["surplus"].values / 1e6, np.column_stack(X)).fit(cov_type="HC1")
    return m.params[0], m.bse[0], len(cl)


b, se, n = fit_scale(d)
scales = [{"scale_kind": "pooled", "trade_season": None, "classes": "2007-2017", "n_classes": n,
           "scale_M": b, "se_M": se}]
log(f"\nSCALE ($M per 100% star chance, average draft year)")
log(f"  pooled (sensitivity), classes 2007-2017: {b:.2f} (se {se:.2f})")
for T in range(2017, 2026):
    bk, sek, nk = fit_scale(d[d["draftYear"] <= T - 9])
    scales.append({"scale_kind": "knowable", "trade_season": T, "classes": f"2007-{T - 9}", "n_classes": nk,
                   "scale_M": bk, "se_M": sek})
    log(f"  knowable, trade season {T}-{str(T + 1)[2:]} (classes 2007-{T - 9}): {bk:.2f} (se {sek:.2f})")

se_ = pd.DataFrame(SEASONS)
se_["surplus_2025_cap"] = (se_["value_share"] - se_["cost_share"]) * CAP_NOW
chk = se_.groupby(["draftYear", "pick"])["surplus_2025_cap"].sum()
m = d.set_index(["draftYear", "pick"])["surplus_before_rights"]
assert (chk.reindex(m.index).fillna(0.0) - m).abs().max() < 1.0      # GUARD: seasons add up to each pick
se_.to_csv(OUTPUT_DIR / "pick_curve_seasons.csv", index=False)
d.to_csv(OUTPUT_DIR / "pick_curve_players.csv", index=False)
pd.DataFrame(scales).to_csv(OUTPUT_DIR / "pick_curve_scales.csv", index=False)
(OUTPUT_DIR / "pick_curve_log.txt").write_text("\n".join(LOG), encoding="utf-8")
log(f"\nwrote pick_curve_players.csv, pick_curve_scales.csv, pick_curve_log.txt in {OUTPUT_DIR}")
