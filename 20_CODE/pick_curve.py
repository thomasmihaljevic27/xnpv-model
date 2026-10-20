"""
pick_curve.py -- the draft pick curve: what a pick is worth, in the player model's dollars.

SPECIFICATION: 00_STATE/MODEL_DIRECTIVES.md directive 6, decided with Thomas on
2026-10-09 step by step (tests and checks in 25_TESTS/pick_*.py). Every rule below
is a recorded decision; the label in brackets says where it was decided or tested.

A PICK'S VALUE
  value = STAR VALUE x Bacon's star probability for the slot    [adopted 2026-10-09]
  * Star chance: SOURCE_DIR/draft_slot_baseline.csv `p_star` (Bacon; a star has
    career WAR per 82 games of 1.8+ forwards / 1.23+ defencemen; his slot
    baseline is a logistic regression on pick number with a kink at pick 150).
    The shape across picks is his; this script fits only the STAR VALUE.
  * STAR VALUE: the surplus a pick would be worth if its player were certain to
    become a star (Thomas's name, 2026-10-09; it replaces "scale"). Each drafted
    player's surplus is regressed on the star probability of his slot, through
    zero [pick_star_form_test.py: through zero won]. v1.7 (Thomas, 2026-10-16): no
    draft-year terms (v1.0-v1.6 had sum-to-zero draft-year indicators).
  * ONE star value for every year (v1.2, Thomas 2026-10-09, option (a)):
      main         fitted on all eleven drafts 2007-2017;
      sensitivity  the same without 2015 and 2016, the two drafts that carry the
                   only trend across drafts [pick_review_checks.py: +2.08 a year with
                   them, +0.84 (p 0.435) without].
    v1.0-v1.1 wrote a trade-season ("knowable") scale as the main one; retired.

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
     each next on the previous offer); from v1.4, once he is eligible for
     arbitration, the higher of the offer and the arbitration price (below),
     each next offer on what he was paid. The entry-level deal runs by CALENDAR
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
     v1.9 (Thomas, 2026-10-19: "Count the 22"): NOT lapsed, and kept, when he signed his
     entry-level deal with the drafting club (elc_signing_dates.csv signing_team, the
     club of the source his signing date comes from): the club held him and lost him
     later (waivers, release). Route "signed by the drafting club". A trade missed by the
     name rule is matched under trades.db's spelling (TRADE_NAMES, hand-verified).
  9. GOALIES are pooled with skaters in one scale [decided 2026-10-09].

v1.6 (2026-10-15, Thomas): DRAFTED PLAYERS WHO DIED BEFORE REACHING THE NHL are left out of every star value
  (deceased_draftees.py: six players of 2007-2017, each "never played" and dead before his control would have
  ended). They stay in pick_curve_players.csv, priced as before and marked excluded_deceased, so every script
  that refits on that file can drop them. The fit drafts' players and picks are otherwise unchanged.

v1.5 (2026-10-14, Thomas: "all aging checks should be consistent"; the arbitration price "should be
consistent with the forecast", reading (a)). Two changes, each also scored alone (scale kinds below):
  * SIGNING AGE. Entry-level length (CBA 9.1(b)) and the arbitration need (12.1(a)) read his age on
    September 15 of the calendar year he SIGNED his entry-level contract (CBA 9.2, 12.1(c)), from
    elc_signing_dates.csv (PuckPedia, then verified CapWages pages). Where no date is held, his first
    NHL season stands in, as before (counted in the log).
  * THE ARBITRATION PRICE'S WAR. Skaters: skater_forecast.ContractForecaster.arbitration_war at page
    y, i.e. xNPV 1's own start at season y (games-weighted 50/30/20 rate per 82 over y-1..y-3, 65/35
    toward comparable players, plus the curve's change to y) times its games share for y, from
    seasons before y only. Goalies: the goalie forecast's construction (contract_npv): 50/30/20
    (62.5/37.5 with two seasons, t-1 alone) shrunk 65% toward the league average. No forecast for
    him at y (no 10+ game season in y-1..y-3 for a skater; no t-1 season for a goalie): he is costed
    at the qualifying offer that season.
  Scale kinds: main and sensitivity (both changes); qo_chain (signing age, no arbitration);
  attribution_v14 (neither: reproduces v1.4's 13.42 exactly, asserted), attribution_signing_age,
  attribution_forecast_arbitration.

THE ARBITRATION COST, ADOPTED as the main cost (v1.4; Thomas 2026-10-13: "I say adopt"; built in v1.3
beside the main one after the supervisor agreed to build and compare; rule: "Use NPV1 price line,
floor it at the QO, same rule for picks and players"). Step 6's qualifying-offer chain without it is
reported beside as the alternative (scale kinds qo_chain, qo_chain_sensitivity; columns *_qo). The
contract engine (rfa_terminal_value v2.4) reads eligibility from PuckPedia's flag; drafted players
keep the CBA count below, because the export starts in 2018-19 and most of their control seasons
come before it.
  * ELIGIBILITY, CBA 2013 Section 12.1(a) (text read 2026-10-13, media.nhl.com/site/asset/public/ext/
    CBA.pdf p.57): first-contract signing age 18-20 needs 4 years of professional experience, 21 needs
    3, 22-23 need 2, 24 and older 1; a year is 10+ NHL games (age 18-19) or 10+ professional games
    under a contract (20+). 12.1(b): only restricted free agents (here: every control season after
    the entry-level deal). 12.1(c): age is as of September 15 of the year he first signs.
    PROXIES (ours): signing age = his age on September 15 of his first NHL season (as for the
    entry-level length); a year of experience = a season of 10+ NHL games, pro-rated in the short
    seasons (6 in 2012-13, 9 in 2019-20, 7 in 2020-21), because the data has no AHL games, so
    eligibility comes later here than in fact (the cost is understated, not overstated).
  * COST of an eligible control season = the higher of the qualifying offer and the MARKET PRICE of his
    50/30/20 trailing WAR: his last three seasons before it, 50/30/20 with the most recent first,
    over seasons with an NHL game (rescaled over the seasons he has), each season's WAR as delivered
    (short seasons to 82 games), priced on the same line as his value (skaters: the contract line,
    one year of term, defence slope; goalies: the goalie line), floored at the league minimum.
  * The next qualifying offer is computed on what he was paid (the arbitration price when higher),
    as the CBA computes it on the prior salary. A season with no NHL game pays the qualifying offer.

TRAILING WEIGHTING CHECK (directive 6): the main cost reads no trailing total; the arbitration
cost (above) reads 50/30/20.

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

SCRIPT_VERSION = "pick_curve.py v1.10 (2026-10-20)"   # v1.10: later drafts priced for the back-test; v1.9: signed by the drafting club kept; v1.8: CBA age on the calendar
load_dotenv()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import skater_forward_projection as sfp          # noqa: E402  skater price line, cap and minimum tables
import rfa_terminal_value as rtv                 # noqa: E402  qualifying-offer formula
import contract_npv as cnpv                      # noqa: E402  goalie price line (recovered on import)
import skater_forecast as SF                     # noqa: E402  v1.5: the arbitration price's WAR (skaters)
import player_season_table as PST                # noqa: E402  v1.5: WAR names -> the forecast's career key
import deceased_draftees as DD                   # noqa: E402  v1.6: drafted players who died before the NHL

SOURCE_DIR, OUTPUT_DIR = Path(os.environ["SOURCE_DIR"]), Path(os.environ["OUTPUT_DIR"])
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


log(SCRIPT_VERSION)
F = {"linkage": OUTPUT_DIR / "draft_pick_linkage.csv", "WAR": SOURCE_DIR / "WAR.csv",
     "GWAR": SOURCE_DIR / "Goalies_WAR.csv", "bacon": SOURCE_DIR / "draft_slot_baseline.csv",
     "trades": SOURCE_DIR / "trades.db", "elc": OUTPUT_DIR / "elc_signing_dates.csv"}
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
ARB_NEED = lambda age: 4 if age <= 20 else 3 if age == 21 else 2 if age <= 23 else 1   # CBA 12.1(a)
ARB_GP = {2012: 6, 2019: 9, 2020: 7}                  # 10 games pro-rated (48/82, 70/82, 56/82), rounded up
W_TRAIL = (0.5, 0.3, 0.2)                            # 50/30/20, most recent season first
V14_STAR = 13.42242755243992                         # v1.4's main star value: the attribution guard
# The price line the recorded tests and V14_STAR were run on (the 2026-10-05 lock). Both guards below run only
# when it is in force: the line was re-locked on 2026-10-14 (September 15 ages), and a new line moves them by
# design. Both passed on that line on 2026-10-14 (session log) before the re-lock.
LINE_OF_TESTS = (-0.0043574069, 0.0174691916, 0.0035971954, 0.0089321965)
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

# v1.5: entry-level signing years (CBA 9.2, 12.1(c)) and the forecaster for the arbitration price
el = pd.read_csv(F["elc"]).dropna(subset=["draftYear", "signing_year"])
SIGNED = {(int(a), int(b)): int(c) for a, b, c in zip(el["draftYear"], el["pick"], el["signing_year"])}
# v1.9: the club he signed his entry-level deal with (NHL code; relocated clubs mapped to the franchise in route())
ELC_TEAM = {(int(a), int(b)): t for a, b, t in zip(el["draftYear"], el["pick"], el["signing_team"]) if pd.notna(t)}
# v1.9 (Thomas, 2026-10-19: "treat P.O. Joseph as traded"): trades.db's spelling where the draft record's defeats the
# name rule. Checked: of the 68 picks v1.8 called lapsed, only this one had a trade of a player with the same surname
# and first initial inside the window (Arizona to Pittsburgh, 2019-06-29).
TRADE_NAMES = {(2017, 23): "Pierre-Olivier Joseph"}
log(f"  entry-level signing years held: {len(SIGNED):,} drafted players (elc_signing_dates.csv)")
FC = SF.ContractForecaster()
CAREERS = set(FC.table["career_key"])
AGE_SRC = {}                                       # (draftYear, pick) -> "signing" / "first NHL season"


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


def career_of(row, s):
    """The forecast's career key for a drafted skater: the WAR names the linkage matched,
    keyed as player_season_table keys careers, keeping the one whose 10+ game seasons cover
    most of his (pick_curve) seasons. None if none of his names is in the forecast's table."""
    if pd.isna(row["war_names"]):
        return None
    best, score = None, -1
    mine = set(s.index[s["GP"] >= 10])
    for nm in str(row["war_names"]).split("|"):
        ck = PST.career_key(nm)
        if ck not in CAREERS:
            continue
        t = FC.table[(FC.table["career_key"] == ck) & (FC.table["GP"] >= 10)]
        sc = len(mine & set(t["syr"]))
        if sc > score:
            best, score = ck, sc
    return best


def market_war(row, s, y, ck):
    """v1.5: the arbitration price's WAR for season y, consistent with the forecast, or None."""
    if row["is_goalie"]:
        def w(z):
            return float(s.loc[z, "WAR"]) * SHORT.get(z, 1.0) if z in s.index and s.loc[z, "GP"] > 0 else None
        w1, w2, w3 = w(y - 1), w(y - 2), w(y - 3)
        if w1 is not None and w2 is not None and w3 is not None:
            tr = 0.5 * w1 + 0.3 * w2 + 0.2 * w3
        elif w1 is not None and w2 is not None:
            tr = 0.625 * w1 + 0.375 * w2
        elif w1 is not None:
            tr = w1
        else:
            return None
        return (1 - cnpv.LAMBDA_G) * tr + cnpv.LAMBDA_G * cnpv.GOALIE_LEAGUE_AVG
    if ck is None:
        return None
    r = FC.arbitration_war(ck, y, y)
    return None if r is None else r[0]


def price(row, s, last, signing=True, forecast_arb=True, record=False, state=None):
    """Summed surplus (cap shares) over the window, under the decided rules. v1.5: `signing`
    reads the CBA ages in the signing year (else his first NHL season); `forecast_arb` prices
    arbitration on the forecast's construction (else the v1.4 raw 50/30/20 season totals)."""
    played = s[(s["GP"] > 0) & (s.index <= last)]
    if played.empty:
        return 0.0, 0.0, 0, 0.0
    first = int(played.index.min())
    key = (int(row["draftYear"]), int(row["overallPickNumber"]))
    sy = SIGNED.get(key) if signing else None
    if record:
        AGE_SRC[key] = "signing" if sy is not None else "first NHL season"
    age = rtv.cba_age(row["birthDate"], sy if sy is not None else first)   # v1.8: on the calendar (was days / 365.25)
    n_elc = 3 if age <= 21 else 2 if age <= 23 else 1
    beta = BETA_D if row["position"] == "D" else BETA_F
    line = (lambda w: ALPHA_G + BETA_G * w) if row["is_goalie"] else (lambda w: ALPHA + beta * w + GAMMA * 1)
    need = ARB_NEED(age)
    ck = None if (row["is_goalie"] or not forecast_arb) else career_of(row, s)
    prior, tot, war_tot = None, 0.0, 0.0
    prior_a, tot_a = None, 0.0                        # the arbitration version's chain and total
    for y in range(int(row["draftYear"]), last + 1):
        in_elc = first <= y < first + n_elc          # by calendar from his first NHL season: no slides
        gp = float(s.loc[y, "GP"]) if y in s.index else 0.0
        arb, m_war = False, None
        if y >= first + n_elc:
            prior = rtv.qualifying_offer(prior or ELC_MAX[row["draftYear"]], prior or ELC_MAX[row["draftYear"]],
                                         y, False)
            qo_a = rtv.qualifying_offer(prior_a or ELC_MAX[row["draftYear"]], prior_a or ELC_MAX[row["draftYear"]],
                                        y, False)
            # ARBITRATION: eligible once his seasons of 10+ NHL games before y reach the CBA 12.1(a) need
            pro = sum(1 for z, g in s["GP"].items() if z < y and g >= ARB_GP.get(z, 10))
            if gp > 0 and pro >= need:
                if forecast_arb:
                    m_war = market_war(row, s, y, ck)
                else:                                 # v1.4: raw 50/30/20 season totals
                    trail = [(wt, float(s.loc[z, "WAR"]) * SHORT.get(z, 1.0))
                             for wt, z in zip(W_TRAIL, (y - 1, y - 2, y - 3)) if z in s.index and s.loc[z, "GP"] > 0]
                    m_war = sum(wt * w for wt, w in trail) / sum(wt for wt, _ in trail) if trail else None
            arb = m_war is not None
            if arb:
                market = max(line(m_war), LMIN[y] / CAP[y]) * CAP[y]
                prior_a = max(qo_a, market)          # floored at the qualifying offer
            else:
                prior_a = qo_a
        if gp == 0:
            continue                                 # no NHL game: worth zero, costs zero
        wins = float(s.loc[y, "WAR"]) * SHORT.get(y, 1.0)
        floor = LMIN[y] / CAP[y]
        raw = line(wins)
        scale = gp / 82 if gp < CAMEO_GP else 1.0
        value = max(raw, floor) * scale
        cost = (ELC_MAX[row["draftYear"]] if in_elc else prior) / CAP[y] * scale
        cost_a = (ELC_MAX[row["draftYear"]] if in_elc else prior_a) / CAP[y] * scale
        tot += value - cost
        tot_a += value - cost_a
        war_tot += wins
        if record:
            SEASONS.append({"draftYear": row["draftYear"], "pick": row["overallPickNumber"], "season": y,
                            "gp": gp, "war_82": wins, "in_entry_level": in_elc, "games_scale": scale,
                            "cap": CAP[y], "value_share": value,
                            # v1.4: cost_share / cost_$ are the adopted (arbitration) cost; *_qo the chain
                            "cost_share": cost_a, "cost_$": (ELC_MAX[row["draftYear"]] if in_elc else prior_a) * scale,
                            "arb_eligible": arb, "arb_market_war": m_war, "cost_qo_share": cost,
                            "cost_qo_$": (ELC_MAX[row["draftYear"]] if in_elc else prior) * scale})
    if state is not None:                             # v1.10: where the adopted chain stands after `last`
        state.update(first=first, n_elc=n_elc, need=need, ck=ck, prior_a=prior_a, signing_age=age)
    return tot_a, war_tot, len(played), tot


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
    key = (int(row["draftYear"]), int(row["overallPickNumber"]))
    if ((ta["key"] == name_key(TRADE_NAMES.get(key, row["playerName"]))) & (ta["date"] > after) & (ta["date"] < ends)).any():
        return "traded first"
    if FRANCHISE.get(ELC_TEAM.get(key), ELC_TEAM.get(key)) == FRANCHISE.get(row["triCode"], row["triCode"]):
        return "signed by the drafting club"            # v1.9: held, then lost later: not lapsed
    return "lapsed"


rows = []
for r in picks.itertuples():
    row = r._asdict()
    s = seasons_of(row)
    end = window_end(row, s)
    last = min(end - 1, LAST_START)
    sur, wins, n, sur_q = price(row, s, last, record=True)   # v1.5: both changes
    v14, _, _, v14_q = price(row, s, last, signing=False, forecast_arb=False)
    sig, _, _, _ = price(row, s, last, signing=True, forecast_arb=False)
    fca, _, _, _ = price(row, s, last, signing=False, forecast_arb=True)
    rt = route(row, s)
    rows.append({"draftYear": r.draftYear, "pick": r.overallPickNumber, "round": r.roundNumber, "player": r.playerName,
                 "playerId": r.playerId, "position": r.position, "is_goalie": r.is_goalie, "team": r.triCode,
                 "window_end": end, "nhl_seasons": n, "war": wins, "route": rt,
                 "surplus_before_rights": sur * CAP_NOW,
                 "surplus": 0.0 if rt in ("lapsed", "drafted twice (earlier pick)") else sur * CAP_NOW,
                 "surplus_qo_before_rights": sur_q * CAP_NOW,
                 "surplus_qo": 0.0 if rt in ("lapsed", "drafted twice (earlier pick)") else sur_q * CAP_NOW,
                 # v1.5 attribution arms (lapsed rights zeroed as above); *_v14_qo feeds the tested-chain guard
                 **{k: 0.0 if rt in ("lapsed", "drafted twice (earlier pick)") else v * CAP_NOW
                    for k, v in (("surplus_v14", v14), ("surplus_signing_only", sig),
                                 ("surplus_forecast_arb_only", fca))},
                 "surplus_v14_qo_before_rights": v14_q * CAP_NOW})
d = pd.DataFrame(rows)
bacon = pd.read_csv(F["bacon"]).set_index("draft_pick")["p_star"]
d["p_star"] = d["pick"].map(bacon)
assert d["p_star"].notna().all()
# v1.6: drafted players who died before reaching the NHL, marked and left out of every fit below
d["excluded_deceased"] = [DD.is_deceased(y, k) for y, k in zip(d["draftYear"], d["pick"])]
for (y, k), (nm, died) in DD.DECEASED.items():
    hit = d[(d["draftYear"] == y) & (d["pick"] == k)]
    assert len(hit) == 1 and hit["route"].iloc[0] == "never played", (y, k, nm)                  # GUARD
    assert int(died[:4]) < int(hit["window_end"].iloc[0]), (nm, died, hit["window_end"].iloc[0])  # GUARD: died in control
    log(f"  excluded from every fit (died before reaching the NHL): {nm}, {y} #{k}, died {died}")

# ---- guards against the tests that decided each step (when their outputs are on this machine) ----
wc = OUTPUT_DIR / "draft_window_count.csv"
if wc.exists():
    w = pd.read_csv(wc)[["draftYear", "overall", "end_g3"]].rename(columns={"overall": "pick"})
    m = d.merge(w, on=["draftYear", "pick"], how="inner")
    log(f"  guard, window ends vs draft_window_count.csv: {int((m['window_end'] == m['end_g3']).sum())} of {len(m)} equal")
    assert (m["window_end"] == m["end_g3"]).all()
ct = OUTPUT_DIR / "pick_cost_and_year_tests.csv"
_L = sfp.XNPV1_RATE
TESTED_LINE = (_L["alpha"], _L["beta"], _L["beta_d_add"], _L["gamma_term"]) == LINE_OF_TESTS
if not TESTED_LINE:
    log("  guard, skater surplus vs pick_cost_and_year_tests: skipped (the price line was re-locked 2026-10-14; "
        "the tests were priced on the 2026-10-05 line)")
if ct.exists() and TESTED_LINE:
    t = pd.read_csv(ct)[["draftYear", "overallPickNumber", "no_slides"]].rename(columns={"overallPickNumber": "pick"})
    m = d.merge(t, on=["draftYear", "pick"], how="inner")
    gap = (m["surplus_v14_qo_before_rights"] / 1e6 - m["no_slides"]).abs()   # the tested chain: v1.4's ages
    log(f"  guard, skater surplus vs pick_cost_and_year_tests no_slides: {int((gap < 1e-6).sum())} of {len(m)} equal")
    assert (gap < 1e-6).all()

log(f"\npicks priced: {len(d):,} ({int(d['is_goalie'].sum())} goalies); played an NHL game: "
    f"{int((d['nhl_seasons'] > 0).sum()):,}")
log("routes: " + ", ".join(f"{k} {v}" for k, v in d["route"].value_counts().items()))
for (y, k), nm in TRADE_NAMES.items():                                       # GUARD: each listed trade is found
    assert d.loc[(d["draftYear"] == y) & (d["pick"] == k), "route"].iloc[0] == "traded first", (y, k, nm)
kept = d[d["route"] == "signed by the drafting club"]
log(f"  signed his entry-level deal with the drafting club, kept (v1.9): {len(kept)} picks, "
    f"${kept['surplus'].sum() / 1e6:,.2f}M")
log(f"surplus zeroed for lapsed rights: ${d.loc[d['surplus'] != d['surplus_before_rights'], 'surplus_before_rights'].sum() / 1e6:,.1f}M "
    f"of ${d['surplus_before_rights'].sum() / 1e6:,.1f}M")

# ---- the scales ------------------------------------------------------------------------------------
def fit_scale(frame):
    frame = frame[~frame["excluded_deceased"]]                     # v1.6: deceased draftees out of every fit
    cl = sorted(frame["draftYear"].unique())
    # v1.7 (Thomas, 2026-10-16: "no intercept and no draft dummies"): surplus on the star chance alone, through
    # zero; the sum-to-zero draft-year columns of v1.0-v1.6 are gone (they moved the star value by $0.004M)
    X = [frame["p_star"].values]
    m = sm.OLS(frame["surplus"].values / 1e6, np.column_stack(X)).fit(cov_type="HC1")
    return m.params[0], m.bse[0], len(cl)


b, se, n = fit_scale(d)
b2, se2, n2 = fit_scale(d[~d["draftYear"].isin([2015, 2016])])
scales = [{"scale_kind": "main", "classes": "2007-2017", "n_classes": n, "scale_M": b, "se_M": se},
          {"scale_kind": "sensitivity", "classes": "2007-2017 without 2015 and 2016", "n_classes": n2,
           "scale_M": b2, "se_M": se2}]
log(f"\nSTAR VALUE ($M at the 2025-26 cap: the surplus of a pick certain to produce a star; through zero, no draft-year terms)")
log(f"  main, all eleven drafts:            {b:.2f} (se {se:.2f})")
log(f"  sensitivity, without 2015 and 2016: {b2:.2f} (se {se2:.2f})")

# ---- the qualifying-offer chain without arbitration, beside the adopted cost (v1.4) ------------------
# GUARD: the adopted cost is never below the chain's in any season (it is floored at a qualifying offer
# that escalates off a salary at least as high), so no pick's surplus is above the chain's.
assert (d["surplus"] <= d["surplus_qo"] + 1.0).all()
dq = d.assign(surplus=d["surplus_qo"])
b3, se3, n3 = fit_scale(dq)
b4, se4, n4 = fit_scale(dq[~dq["draftYear"].isin([2015, 2016])])
scales += [{"scale_kind": "qo_chain", "classes": "2007-2017", "n_classes": n3, "scale_M": b3, "se_M": se3},
           {"scale_kind": "qo_chain_sensitivity", "classes": "2007-2017 without 2015 and 2016", "n_classes": n4,
            "scale_M": b4, "se_M": se4}]
log(f"  the qualifying-offer chain (main until 2026-10-13): {b3:.2f} (se {se3:.2f}); without 2015 and 2016 "
    f"{b4:.2f} (se {se4:.2f})")
# v1.5 attribution: each change alone and both, same rows and regression
att = {}
for kind, col in (("attribution_v14", "surplus_v14"), ("attribution_signing_age", "surplus_signing_only"),
                  ("attribution_forecast_arbitration", "surplus_forecast_arb_only")):
    bb, ss_, nn = fit_scale(d.assign(surplus=d[col]))
    att[kind] = bb
    scales.append({"scale_kind": kind, "classes": "2007-2017", "n_classes": nn, "scale_M": bb, "se_M": ss_})
if TESTED_LINE:
    assert abs(att["attribution_v14"] - V14_STAR) < 1e-9, (att["attribution_v14"], V14_STAR)   # GUARD
log(f"  v1.5 attribution (all eleven drafts): v1.4 rules {att['attribution_v14']:.2f}"
    f"{' (reproduces v1.4)' if TESTED_LINE else ' (on the re-locked line)'}; signing age alone "
    f"{att['attribution_signing_age']:.2f}; forecast-consistent arbitration alone "
    f"{att['attribution_forecast_arbitration']:.2f}; both (main) {b:.2f}")
src = pd.Series(AGE_SRC)
log(f"  CBA ages read in the signing year for {int((src == 'signing').sum()):,} of {len(src):,} players who played; "
    f"first NHL season stands in for {int((src != 'signing').sum()):,}")
sa = pd.DataFrame(SEASONS)
log(f"  control seasons played: {int((~sa['in_entry_level'] & (sa['cost_qo_$'] > 0)).sum()):,}; "
    f"priced at arbitration: {int(sa['arb_eligible'].sum()):,}; "
    f"priced above the qualifying offer: {int((sa['cost_$'] > sa['cost_qo_$'] + 1).sum()):,}")
fr = sa.merge(d[["draftYear", "pick", "route"]], on=["draftYear", "pick"])
fr = fr[fr["route"].isin(["same team", "traded first"])]
log("  first-round picks who played, summed over their control windows ($M at the 2025-26 cap):")
for lo, hi in ((1, 10), (11, 32)):
    g = fr[fr["pick"].between(lo, hi)]
    v, c, cq = (g[k].sum() * CAP_NOW / 1e6 for k in ("value_share", "cost_share", "cost_qo_share"))
    log(f"    picks {lo}-{hi}: value delivered {v:,.1f}; cost {c:,.1f} ({c / cq:.2f}x the qualifying-offer "
        f"chain's {cq:,.1f})")

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


# ---- v1.10 (2026-10-20, the back-test; Thomas: "Played + rest re-valued", "The model's rule"): the 2018-2025 drafts --
# Priced by the same rules (price(), route(), window_end()) through 2025-26, for the back-test's outcomes of traded
# picks and prospects. NOT in any fit: this block runs after every fit and every file above is written, and writes
# its own two files. Entry-level maximum by draft year, 2020 MOU: $925,000 to the 2021 draft, $950,000 for 2022-2023,
# $975,000 for 2024-2025 (PuckPedia's summary of the 2020 MOU, read 2026-10-20).
LATER = range(2018, 2026)
ELC_MAX.update({2018: 925_000, 2019: 925_000, 2020: 925_000, 2021: 925_000, 2022: 950_000, 2023: 950_000,
                2024: 975_000, 2025: 975_000})
n_fit_seasons = len(SEASONS)
later = link[link["draftYear"].isin(LATER)].copy()
later["is_goalie"] = later["is_goalie"].astype(bool)
later = later[(later["link_status"] != "excluded_merged_name") & later["birthDate"].notna()]
lrows = []
for r in later.itertuples():
    row = r._asdict()
    s = seasons_of(row)
    end = window_end(row, s)
    last = min(end - 1, LAST_START)
    st = {}
    sur, wins, n, sur_q = price(row, s, last, record=True, state=st)
    rt = route(row, s)
    lrows.append({"draftYear": r.draftYear, "pick": r.overallPickNumber, "round": r.roundNumber, "player": r.playerName,
                  "playerId": r.playerId, "position": r.position, "is_goalie": r.is_goalie, "team": r.triCode,
                  "birthDate": r.birthDate, "war_names": r.war_names, "window_end": end, "nhl_seasons": n, "war": wins,
                  "route": rt, "surplus_before_rights": sur * CAP_NOW,
                  "surplus": 0.0 if rt in ("lapsed", "drafted twice (earlier pick)") else sur * CAP_NOW,
                  # where the adopted cost chain stands after 2025-26 (empty when he has not played)
                  "chain_first": st.get("first"), "chain_n_elc": st.get("n_elc"), "chain_need": st.get("need"),
                  "chain_prior": st.get("prior_a"), "career_key": st.get("ck")})
ld = pd.DataFrame(lrows)
ls = pd.DataFrame(SEASONS[n_fit_seasons:])
if len(ls):
    ls["surplus_2025_cap"] = (ls["value_share"] - ls["cost_share"]) * CAP_NOW
    chk = ls.groupby(["draftYear", "pick"])["surplus_2025_cap"].sum()
    m = ld.set_index(["draftYear", "pick"])["surplus_before_rights"]
    assert (chk.reindex(m.index).fillna(0.0) - m).abs().max() < 1.0      # GUARD: seasons add up to each pick
assert len(SEASONS) - n_fit_seasons == len(ls) and len(pd.DataFrame(SEASONS[:n_fit_seasons])) == len(se_)   # GUARD: fit rows untouched
ld.to_csv(OUTPUT_DIR / "pick_curve_later_players.csv", index=False)
ls.to_csv(OUTPUT_DIR / "pick_curve_later_seasons.csv", index=False)
log()
log(f"LATER DRAFTS (2018-2025), priced for the back-test only, in no fit: {len(ld):,} picks, {len(ls):,} seasons "
    f"played; surplus through 2025-26 ${ld['surplus'].sum() / 1e6:,.1f}M; routes: "
    + ", ".join(f"{k} {v}" for k, v in ld["route"].value_counts().items()))
log("wrote pick_curve_later_players.csv and pick_curve_later_seasons.csv")
(OUTPUT_DIR / "pick_curve_log.txt").write_text("\n".join(LOG), encoding="utf-8")
