"""
prospect_values.py -- the prospect model: what each prospect in the trade inventory was worth when he was traded,
from his draft slot, the seasons since his draft, his production adjusted to NHL terms and his age (v1.2).

SPECIFICATION: 00_STATE/MODEL_DIRECTIVES.md directive 6, "Prospects, step one" (Thomas, 2026-10-14). Every
rule below is a recorded decision; the bracket says where.

WHO IS A PROSPECT [opening decision 2]
  A drafted player the player model does not take yet at the valuation season y:
  * skaters: no NHL season of 10+ games in the three before y (forecast_config.MIN_GP; the skater forecast's
    three-season anchor);
  * goalies: no NHL game in the six seasons before y (the goalie forecast takes any NHL season in the three
    before, walking back up to three more: contract_npv.shrunk_projection, STALE_MAXBACK = 3).
  A player the player model takes is valued there, not here. Undrafted players: see UNDRAFTED below (v1.3).

WHAT HE IS WORTH [opening decisions 1 and 3]
  value = Bacon's star chance for his slot (draft_slot_baseline.csv p_star) x STAR VALUE(k),
  k = seasons since his draft = y - draft year (k = 0: the season starting the autumn after his draft, the
  pick curve's first season). The currency is the pick curve's: remaining NHL seasons priced on the contract
  line minus his cost (entry-level deal, then the qualifying offer or the arbitration price), to the end of
  club control, at the 2025-26 cap.
  * STAR VALUE(k): pick_curve.fit_scale's regression (through zero; v1.10: no draft-year terms;
    robust HC1 errors) on the 2007-2017 drafted players who were prospects at k, outcome their remaining
    surplus: pick_curve_seasons.csv's priced seasons from y on (season y in full), lapsed rights zeroed as the
    pick curve zeroes them. k = 0, 1, 2, 3 one fit each; 4 and later one fit on the stacked rows for k = 4..7,
    errors clustered by player. Kept: the through-zero form (Thomas, 2026-10-14), the pick curve's current
    form; the free-constant alternative is an open choice (WORK_QUEUE).
  * Past the end of club control (CBA Group 3, as pick_curve.window_end: 27 as of June 30, or seven Accrued
    Seasons) a prospect is worth zero: nothing is left to control.
  That is step one; from v1.2 it is reported beside as value_slot_only_M, and goalies keep it as their value.

STEP TWO, PRODUCTION AND AGE (v1.2; MODEL_DIRECTIVES directive 6, "Prospects, step two" and "age"; Thomas
2026-10-14, each choice his; measured by 25_TESTS/prospect_nhle_look.py v1.1 and prospect_age_look.py v1.0)
  * Production: NHL-equivalent points per 82 games = Elite Prospects points x the league-season's NHLe factor
    (nhle_temporal.csv), over his games that season; seasons of 10+ games; 2012-13's missing factor = the mean
    of the league's 2011-12 and 2013-14; his level 50/30/20 over the three seasons before the valuation season,
    rescaled over those he has; none: a no-record indicator. Curved: the level and its square (v1.7: the square as
    it is, in squared points; v1.2-v1.6 stored it divided by 10, a scale change only).
  * Age: years past first eligibility = his age on September 15 of the valuation season (the CBA date), minus
    seasons since the draft, minus 18 (v1.7; 18.5 before, the same values: production's coefficient absorbs the
    shift). It enters as production x years past first eligibility (the same
    scoring counts for less from an older prospect), in seasons 0-3 since the draft only.
  * The slot's star chance enters in seasons 0-2 only; from season 3, production alone.
  * value_M (main) = the fitted line for his season group: seasons 0-2 star chance + level + level squared +
    no-record + production x age; season 3 the same without the star chance; 4+ without age. v1.7 (Thomas,
    2026-10-15): "Age is fully adopted and we don't need to report an age removed version as sensitivity", so
    value_no_age_M (v1.2-v1.6) is gone. Each fit is the pick curve's form (through zero;
    v1.10: no draft-year terms; errors robust, clustered by player for 4+) on the 2007-2017 skater
    rows still prospects (13,152 rows, 2,089 players).
  * Goalies: the slot alone (NHLe measures scoring).

UNDRAFTED (v1.3; Thomas 2026-10-14: "NHL contracts only", "Same model, no slot"; also players drafted before 2005)
  * NHL rights only through an NHL contract: a cap hit without trades.db's AHL/junior flag, or a PuckPedia contract
    of his (standard or entry level, i.e. NHL) running on the trade date. trades.db lists a player assigned to the
    AHL at $0 with the flag although his NHL two-way contract runs, so PuckPedia decides; without an NHL id, a
    PuckPedia contract of the same name running on the trade date, whatever its cap hit, supplies it (one id only).
  * With an NHL contract: the drafted model with the star chance at zero (the slot term drops out), seasons since
    the draft counted from his first draft-eligible year (the first draft at which he was 18 by September 15),
    production and age as for anyone; birthdate and Elite Prospects id from PuckPedia; past club control zero;
    goalies zero (the slot alone, and he has none). Fitted on drafted players: it assumes an undrafted player
    converts like a drafted one at the same production (a stated limitation).
  * Without one: zero (no NHL rights), or signing rights to a player whose contract has expired: zero. Traded
    before 2018-07-01 with no contract seen: not valued (PuckPedia's export holds contracts running in 2018-19 or
    later, so an earlier one cannot be seen).
  * A value can be below zero: a low scorer's remaining surplus averages slightly below zero in the data, and
    negative careers count, as in the pick curve.
  GUARD: every step-two fit equals the look that measured it, to 1e-9 (when those outputs are present).
  * ONE REGRESSION (v1.8, Thomas 2026-10-16: "Just make the regression actually be the interaction terms"): the star
    values and each step-two version are one regression on every prospect-season (fit_stacked), each term (and, to
    v1.9, each draft's level) multiplied by an indicator for the season group (a full set of interaction terms), errors
    clustered by player (one player appears in several seasons). The coefficients equal the season-by-season fits
    (GUARD, 1e-9; those fits stay for the each-draft-left-out values); only the standard errors move, and only by
    the small-sample correction (a season's rows hold each player once, so its block of the clustered variance is
    the season's own).
  * DECEASED DRAFTEES (v1.6, Thomas 2026-10-15): the six drafted players of 2007-2017 who died before reaching
    the NHL (pick_curve_players.csv excluded_deceased; deceased_draftees.py) are left out of the star values and
    of every step-two fit, all their rows.
  * THE OVERLAP [opening decision 4]: a 2007-2017 draftee sits inside the fit that values him. Stated as a
    limitation; his value with his own draft left out of the fit is reported beside (value_own_draft_out_M).

THE TRADE INVENTORY (trades.db, player assets, from 2017-07-01 as for traded picks; trade season = the season
starting July 1 on or before the trade date; valuation season y = the trade's page (trade_page.page: the trade
season, or the next one for a trade after that season's last regular-season game; v1.5, Thomas 2026-10-14), or his
draft year when he is traded between his draft and July 1).
  WHO EACH TRADED PLAYER IS (v1.1, Thomas 2026-10-14: "determine the O'Reilly fix needed and also fix name
  matching"). Ours, in this order:
  1. HIS NHL ID, from PuckPedia (identity only; no value is read from it): a PuckPedia trade row of the same name
     within 3 days of the trade (PuckPedia's trade rows start in 2019), or a PuckPedia contract of the same name
     whose cap hit equals the asset's (trades.db cap_hit_aav) and which runs on the trade date (signed on or
     before it, ending June 30 of its last season on or after it). "Same name" = same surname and first names
     that agree as canonical forms or on the first letter. One id: he is the drafted player with that NHL id
     (draft_pick_linkage playerId; drafted twice, the later draft), or not a 2005-2026 draftee when no drafted
     player has it. Two ids or none: the name rules decide.
  2. NAMES (v1.0, widened): surname plus a canonical first name (pick_curve.name_key's short forms, widened with
     nic/nicolas, nate, phil, sammy, evgenii, yegor), initials joined ("P.O Joseph" = "Pierre-Olivier Joseph"),
     hyphens read as spaces, against the linkage's name AND Elite Prospects' name for the same draft slot; only
     players whose draft had begun by the trade date; a NAMESAKE GUARD: a draftee with no NHL record
     (zero_no_nhl_record) is rejected when the name has NHL seasons between his draft and the trade (those
     seasons are someone else's; seasons before his draft are an older namesake's and do not reject him).
     Two or more left: not valued, listed (ambiguous).
  Both rules are run on every asset and every disagreement is listed in the log. v1.1 run: 684 of 927 assets
  matched by NHL id; the names agree on 682; the two differences were v1.0's errors: Ryan O'Reilly traded
  2018-07-01 (the 2009 #33 veteran, by his $7.5M contract; v1.0 left him ambiguous with a 2018 draftee of the
  same name) and Mikko Lehtonen traded 2021 (not a draftee; v1.0 matched the 2005 #83 namesake).

TRAILING WEIGHTING CHECK (directive 6): production reads 50/30/20 (W_NHLE), rescaled over the seasons he has; the
surplus it fits on carries the pick curve's arbitration price, which reads the forecast's 50/30/20 (pick_curve.py v1.5).

INPUTS: OUTPUT_DIR/pick_curve_players.csv, pick_curve_seasons.csv, pick_curve_scales.csv (pick_curve.py),
OUTPUT_DIR/draft_pick_linkage.csv, OUTPUT_DIR/draft_raw/draft_YYYY.json, OUTPUT_DIR/ep_out/ep_prospects.db
(Elite Prospects draft names and skater seasons), SOURCE_DIR/nhle_temporal.csv, trades.db, WAR.csv, Goalies_WAR.csv, draft_slot_baseline.csv, and the
PuckPedia contract and trade exports (through contract_source.py; NHL ids only).
OUTPUTS: OUTPUT_DIR/prospect_values.csv (one row per traded player asset), prospect_star_values.csv (step one's
star value for each k, and with each draft left out), prospect_production_fits.csv (step two's coefficients, each
version and season group, all drafts and each left out), prospect_values_log.txt.

Run from the repo root:  python 20_CODE/prospect_values.py   (after pick_curve.py)
"""

import json
import os
import re
import sqlite3
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv


SCRIPT_VERSION = "prospect_values.py v1.10 (2026-10-16)"   # v1.10: no draft-year terms (Thomas); v1.9: PuckPedia dates
load_dotenv()
import contract_source as CS   # noqa: E402  v1.1: PuckPedia exports read strictly (identity only)
SOURCE_DIR, OUTPUT_DIR = Path(os.environ["SOURCE_DIR"]), Path(os.environ["OUTPUT_DIR"])

# ---- constants (each from the specification above) ----------------------------------------------
SKATER_GP, SKATER_BACK = 10, 3        # skater forecast: a 10+ game season in the three before
GOALIE_BACK = 6                       # goalie forecast: three before, walk-back up to three more
POOL_FROM, K_MAX = 4, 7               # k = 0..3 one fit each; 4+ one fit on k = 4..7
LAST_START = 2025                     # 2025-26, the last season in the data (start year)
FIT_CLASSES = range(2007, 2018)       # the pick curve's drafts
LAPSED = ("lapsed", "drafted twice (earlier pick)")
TRADES_FROM = "2017-07-01"
PP_FROM = pd.Timestamp(2018, 7, 1)     # v1.3: PuckPedia's contract export holds contracts running in 2018-19 or later
ACCRUE_PRORATE = {2012: 48 / 82, 2019: 70 / 82, 2020: 56 / 82}   # as pick_curve (Accrued Season thresholds)
FIRST_FORMS = {"tony": "anthony", "josh": "joshua", "mike": "michael", "alex": "alexander", "matt": "matthew",
               "nick": "nicholas", "will": "william", "zach": "zachary", "jake": "jacob", "dan": "daniel",
               "danny": "daniel", "chris": "christopher", "sam": "samuel", "ben": "benjamin", "tom": "thomas",
               "jon": "jonathan", "joe": "joseph", "andy": "andrew", "nate": "nathan", "max": "maxim",
               "steve": "steven", "rob": "robert", "bobby": "robert",           # pick_curve.SHORT_FORMS
               "nic": "nicholas", "nicolas": "nicholas", "phil": "philip", "sammy": "samuel",   # added here
               "evgenii": "evgeni", "yegor": "egor"}
# v1.1: assets where the NHL id and the name rules disagree, each read on 2026-10-14 (the id is right in both)
REVIEWED_DISAGREEMENTS = {("2018-07-01", "Ryan O'Reilly"),      # the 2009 #33 veteran ($7.5M), not the 2018 #98 draftee
                          ("2021-03-12", "Mikko Lehtonen")}     # the KHL defenceman, not the 2005 #83 draftee
INITIAL_FORMS = {"po joseph": "pierre olivier joseph", "jf berube": "jean francois berube"}   # after joining

LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


def norm(s):
    """pick_curve.norm, with hyphens read as spaces: strip accents, lowercase, letters and spaces."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z ]", "", s.lower().replace("-", " ").replace(".", " "))
    return re.sub(r"\s+", " ", s).strip()


def name_key(s):
    n = re.sub(r"\b([a-z]) (?=[a-z]\b)", r"\1", norm(s))   # initials joined: "p o joseph" -> "po joseph"
    n = INITIAL_FORMS.get(n, n)
    parts = n.split()
    if len(parts) < 2:
        return (n, "")
    return (parts[-1], " ".join(FIRST_FORMS.get(x, x) for x in parts[:-1]))


def year_reaching(birth, age):
    """pick_curve.year_reaching: END-year of the first League Year at whose June 30 he is `age` or older."""
    return birth.year + age + (1 if (birth.month, birth.day) > (6, 30) else 0)


def window_end(birth, is_goalie, seasons):
    """pick_curve.window_end: END-year of his last controlled season (CBA Group 3)."""
    base = 30 if is_goalie else 40
    accrued = sorted(y + 1 for y, g in seasons["GP"].items() if g >= base * ACCRUE_PRORATE.get(y, 1.0))
    y27 = year_reaching(birth, 27)
    return min(y27, accrued[6]) if len(accrued) >= 7 else y27


def is_prospect(seasons, y, is_goalie):
    """True when the player model does not take him at season y (rule above). `seasons`: GP by start year."""
    before = seasons[(seasons.index < y) & (seasons["GP"] > 0)]
    if is_goalie:
        return not (before.index >= y - GOALIE_BACK).any()
    return not ((before.index >= y - SKATER_BACK) & (before["GP"] >= SKATER_GP)).any()


def k_group(k):
    return str(k) if k < POOL_FROM else f"{POOL_FROM}+"


# ---- the star values ----------------------------------------------------------------------------------
def fit(frame, cluster=False):
    """pick_curve.fit_scale on remaining surplus: through zero, no draft-year terms (v1.10)."""
    X = np.column_stack([frame["p_star"].values])
    if cluster:
        groups = pd.factorize(frame["draftYear"].astype(str) + "-" + frame["pick"].astype(str))[0]
        m = sm.OLS(frame["remaining_M"].values, X).fit(cov_type="cluster", cov_kwds={"groups": groups})
    else:
        m = sm.OLS(frame["remaining_M"].values, X).fit(cov_type="HC1")
    return float(m.params[0]), float(m.bse[0])


def star_values():
    """The star value for each k group, and with each 2007-2017 draft left out. Returns (table, rows)."""
    p = pd.read_csv(OUTPUT_DIR / "pick_curve_players.csv")
    p = p[~p["excluded_deceased"].astype(bool)]                 # v1.6: drafted players who died before the NHL
    s = pd.read_csv(OUTPUT_DIR / "pick_curve_seasons.csv")
    lapsed = p.loc[p["route"].isin(LAPSED), ["draftYear", "pick"]].assign(lapsed=True)
    s = s.merge(lapsed, on=["draftYear", "pick"], how="left")
    s["sur_M"] = np.where(s["lapsed"].fillna(False).astype(bool), 0.0, s["surplus_2025_cap"] / 1e6)
    by_player = {key: g.set_index("season").rename(columns={"gp": "GP"}) for key, g in s.groupby(["draftYear", "pick"])}
    empty = s.iloc[0:0].set_index("season").rename(columns={"gp": "GP"})
    rows = []
    for r in p.itertuples():
        mine = by_player.get((r.draftYear, r.pick), empty)
        for k in range(0, K_MAX + 1):
            y = r.draftYear + k
            if y > LAST_START:
                break
            rows.append({"draftYear": r.draftYear, "pick": r.pick, "p_star": r.p_star, "k": k,
                         "prospect": is_prospect(mine, y, bool(r.is_goalie)),
                         "remaining_M": float(mine.loc[mine.index >= y, "sur_M"].sum())})
    d = pd.DataFrame(rows)
    d["k_group"] = d["k"].map(lambda k: k_group(min(k, K_MAX)))
    out = []
    pr = d[d["prospect"]]
    # v1.8: one regression, the star chance interacted with each season group (v1.10: no draft levels)
    st, _ = fit_stacked(pr, {grp: ["p_star"] for grp in pr["k_group"].astype(str).unique()})
    for grp, g in pr.groupby("k_group", sort=True):
        clus = grp.endswith("+")
        b_own, _ = fit(g, clus)
        b, se = float(st[grp][0][0]), float(st[grp][1][0])
        assert abs(b - b_own) < 1e-9, grp                               # GUARD: the stack equals the season's own fit
        out.append({"k_group": grp, "left_out": "none", "star_value_M": b, "se_M": se, "rows": len(g)})
        for c in sorted(g["draftYear"].unique()):
            bb, ss = fit(g[g["draftYear"] != c], clus)
            out.append({"k_group": grp, "left_out": str(c), "star_value_M": bb, "se_M": ss,
                        "rows": int((g["draftYear"] != c).sum())})
    return pd.DataFrame(out), d


# ---- step two: production adjusted to NHL terms, and age (v1.2) ---------------------------------------
PROD_MIN_GP = 10                      # a production season counts with 10+ games [step two, "accept all"]
W_NHLE = (0.5, 0.3, 0.2)              # 50/30/20 over the three seasons before, most recent first [directive 6]
FIRST_ELIGIBLE_AGE = 18.0             # v1.7: years past first eligibility = age the autumn after the draft - 18
SLOT_GROUPS = ("0", "1", "2")         # the slot enters in these season groups only [step two]
AGE_GROUPS = ("0", "1", "2", "3")     # the age discount applies in these only [age, "Seasons 0-3 only"]
VERSIONS = ("main",)                  # v1.7: the age-removed version is gone (Thomas, 2026-10-15)


def production_rates():
    """{(Elite Prospects id, season start year): NHL-equivalent points per 82} for seasons of 10+ games.
    Points x the league-season's NHLe factor (nhle_temporal.csv), summed over his teams, over his games.
    2012-13 has no factor: the mean of the league's 2011-12 and 2013-14 [step two, "accept all"]."""
    nh = pd.read_csv(SOURCE_DIR / "nhle_temporal.csv")
    fac = {(r.league, int(r.season_start_year)): float(r.nhle) for r in nh.itertuples()}
    for lg in nh["league"].unique():
        if (lg, 2012) not in fac and (lg, 2011) in fac and (lg, 2013) in fac:
            fac[(lg, 2012)] = (fac[(lg, 2011)] + fac[(lg, 2013)]) / 2
    con = sqlite3.connect(OUTPUT_DIR / "ep_out" / "ep_prospects.db")
    s = pd.read_sql("select ep_player_id, season, league, gp, tp from ep_skater_seasons", con)
    s["syr"] = s["season"].str[:4].astype(int)
    s["ep_player_id"] = pd.to_numeric(s["ep_player_id"]).astype(int).astype(str)
    s["gp"], s["tp"] = pd.to_numeric(s["gp"], errors="coerce"), pd.to_numeric(s["tp"], errors="coerce")
    s = s[(s["gp"] > 0) & s["tp"].notna()].copy()
    s["f"] = [fac.get((lg, y)) for lg, y in zip(s["league"], s["syr"])]
    s = s[s["f"].notna()]                           # a league-season without a factor: its games left out
    s["nhle_pts"] = s["tp"] * s["f"]
    g = s.groupby(["ep_player_id", "syr"]).agg(gp=("gp", "sum"), nhle_pts=("nhle_pts", "sum"))
    g = g[g["gp"] >= PROD_MIN_GP]
    return (g["nhle_pts"] / g["gp"] * 82).to_dict()


def production_features(frame, rates):
    """Adds the step-two inputs to rows with ep_player_id, birthDate, season (y) and k:
    nhle82 (50/30/20 over y-1..y-3, rescaled over the seasons he has), nhle82_sq (squared, v1.7), no_record,
    past_elig (age on September 15 of y, minus k, minus 18) and prod_x_age."""
    lv, n = [], []
    for ep, y in zip(frame["ep_player_id"], frame["season"]):
        got = [(w, rates[(ep, z)]) for w, z in zip(W_NHLE, (y - 1, y - 2, y - 3)) if (ep, z) in rates]
        lv.append(sum(w * r for w, r in got) / sum(w for w, _ in got) if got else 0.0)
        n.append(len(got))
    frame = frame.copy()
    frame["nhle82"], frame["n_prod_seasons"] = lv, n
    frame["nhle82_sq"] = frame["nhle82"] ** 2
    frame["no_record"] = (frame["n_prod_seasons"] == 0).astype(float)
    age = (pd.to_datetime(frame["season"].astype(int).astype(str) + "-09-15") - frame["birthDate"]).dt.days / 365.25
    frame["past_elig"] = age - frame["k"] - FIRST_ELIGIBLE_AGE
    frame["prod_x_age"] = frame["nhle82"] * frame["past_elig"]
    return frame


def cols_for(group, version):
    return ((["p_star"] if group in SLOT_GROUPS else []) + ["nhle82", "nhle82_sq", "no_record"]
            + (["prod_x_age"] if version == "main" and group in AGE_GROUPS else []))


def fit_cols(frame, cols, cluster):
    """The pick curve's form: through zero, no draft-year terms (v1.10)."""
    X = np.column_stack([frame[c].values for c in cols])
    if cluster:
        groups = pd.factorize(frame["draftYear"].astype(str) + "-" + frame["pick"].astype(str))[0]
        m = sm.OLS(frame["remaining_M"].values, X).fit(cov_type="cluster", cov_kwds={"groups": groups})
    else:
        m = sm.OLS(frame["remaining_M"].values, X).fit(cov_type="HC1")
    return m.params[:len(cols)], m.bse[:len(cols)]


def fit_stacked(frame, cols_by_group, group_col="k_group"):
    """One regression on every row of frame: for each season group g, each column in cols_by_group[g] multiplied by
    the indicator for g (v1.10: no draft-year terms). A full set of interaction terms, through zero, so the design
    is block-diagonal and each group's coefficients equal the
    group's own fit_cols (checked by the callers). Errors clustered by player (draftYear-pick) across the stack.
    Returns ({g: (params, bse)} for the cols of each group, the fitted model)."""
    gv = frame[group_col].astype(str).values
    blocks, at, pos = [], {}, 0
    for g in sorted(cols_by_group):
        on = gv == g
        assert on.any(), g
        cols = cols_by_group[g]
        # np.where, not multiplication: another group's NaN times zero would still be NaN
        blocks += [np.where(on, frame[c].values, 0.0) for c in cols]
        at[g] = (pos, len(cols))
        pos += len(cols)
    assert set(gv) <= set(cols_by_group), "rows outside the listed groups"
    players = pd.factorize(frame["draftYear"].astype(str) + "-" + frame["pick"].astype(str))[0]
    m = sm.OLS(frame["remaining_M"].values, np.column_stack(blocks)).fit(
        cov_type="cluster", cov_kwds={"groups": players})
    m.positions = at                                     # {g: (first column, number of cols)}, for joint tests
    return {g: (m.params[p:p + n], m.bse[p:p + n]) for g, (p, n) in at.items()}, m


def production_fits(fitrows, rates):
    """Step two's coefficients for each version and season group, on all drafts and with each draft left out.
    Training rows: the step-one rows of skaters still prospects (goalies stay on the slot alone)."""
    pl = pd.read_csv(OUTPUT_DIR / "pick_curve_players.csv")[["draftYear", "pick", "is_goalie"]]
    link = pd.read_csv(OUTPUT_DIR / "draft_pick_linkage.csv", parse_dates=["birthDate"])
    link = link[["draftYear", "overallPickNumber", "birthDate"]].rename(columns={"overallPickNumber": "pick"})
    ep = pd.read_sql("select draft_year draftYear, draft_overall pick, ep_player_id from ep_draft_selections",
                     sqlite3.connect(OUTPUT_DIR / "ep_out" / "ep_prospects.db"))
    d = fitrows[fitrows["prospect"]].merge(pl, on=["draftYear", "pick"], how="left")
    d = d[~d["is_goalie"].astype(bool)].merge(link, on=["draftYear", "pick"], how="left").merge(
        ep, on=["draftYear", "pick"], how="left")
    assert d["birthDate"].notna().all() and d["ep_player_id"].notna().all()
    d["ep_player_id"] = pd.to_numeric(d["ep_player_id"]).astype(int).astype(str)
    d["season"] = d["draftYear"] + d["k"]
    d = production_features(d.reset_index(drop=True), rates)
    fits = {}
    for v in VERSIONS:
        # v1.8: one regression with the full set of interaction terms gives the coefficients and their errors
        groups = sorted(d["k_group"].astype(str).unique())
        st, _ = fit_stacked(d, {g: cols_for(g, v) for g in groups})
        for g, x in d.groupby("k_group"):
            cols = cols_for(g, v)
            b_own, _ = fit_cols(x, cols, g.endswith("+"))
            b, se = st[g]
            assert np.max(np.abs(b - b_own)) < 1e-9, (v, g)          # GUARD: the stack equals the season's own fit
            fits[(v, g, "none")] = (cols, b, se)
            for c in sorted(x["draftYear"].unique()):
                fits[(v, g, int(c))] = (cols, fit_cols(x[x["draftYear"] != c], cols, g.endswith("+"))[0], None)
    return fits, d


# ---- NHL seasons by name (as pick_curve.season_table) -----------------------------------------------
FRANCHISE = {"N.J": "NJD", "S.J": "SJS", "T.B": "TBL", "L.A": "LAK", "ATL": "WPG", "PHX": "ARI", "UTA": "ARI"}


def season_table(path, name_col):
    w = pd.read_csv(path, usecols=[name_col, "Season", "GP", "WAR"])
    w["name_n"] = w[name_col].map(norm)
    w["start"] = w["Season"].map(lambda x: 2000 + int(str(x)[:2]))
    return w.groupby(["name_n", "start"]).agg(GP=("GP", "sum"), WAR=("WAR", "sum"))


def main():
    log(SCRIPT_VERSION)
    F = {"pick_curve_players": OUTPUT_DIR / "pick_curve_players.csv",
         "pick_curve_seasons": OUTPUT_DIR / "pick_curve_seasons.csv",
         "pick_curve_scales": OUTPUT_DIR / "pick_curve_scales.csv",
         "linkage": OUTPUT_DIR / "draft_pick_linkage.csv", "trades": SOURCE_DIR / "trades.db",
         "WAR": SOURCE_DIR / "WAR.csv", "GWAR": SOURCE_DIR / "Goalies_WAR.csv",
         "bacon": SOURCE_DIR / "draft_slot_baseline.csv"}
    for k, p in F.items():
        log(f"  input {k}: {p.resolve()}  (modified {pd.Timestamp(p.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M})")
    log(f"  pick curve: {(OUTPUT_DIR / 'pick_curve_log.txt').read_text(encoding='utf-8').splitlines()[0]}")

    # ---- 1. the star values -----------------------------------------------------------------------
    sv, fitrows = star_values()
    main_sv = sv[sv["left_out"] == "none"].set_index("k_group")
    curve_main = pd.read_csv(F["pick_curve_scales"]).set_index("scale_kind").loc["main", "scale_M"]
    assert abs(main_sv.loc["0", "star_value_M"] - curve_main) < 1e-9          # GUARD: k = 0 is the pick curve
    log(f"\n  guard: at the draft the star value reproduces the pick curve's {curve_main:.4f} (PASS)")
    chk = OUTPUT_DIR / "prospect_slot_years.csv"                                # the check that measured step one
    if chk.exists():
        c = pd.read_csv(chk, dtype={"seasons_since_draft": str}).set_index("seasons_since_draft")["star_value_M"]
        gap = max(abs(main_sv.loc[g, "star_value_M"] - c[g]) for g in main_sv.index)
        assert gap < 1e-9, gap                                                   # GUARD
        log(f"  guard: star values equal prospect_slot_years_check.py's for {len(main_sv)} of {len(main_sv)} groups (PASS)")
    log("\nSTAR VALUE FOR A PLAYER STILL A PROSPECT ($M at the 2025-26 cap), by seasons since the draft")
    for g, r in main_sv.iterrows():
        lo = sv[(sv["k_group"] == g) & (sv["left_out"] != "none")]["star_value_M"]
        log(f"  {g:>2}: {r.star_value_M:6.2f} (se {r.se_M:.2f}); each draft left out {lo.min():.2f} to {lo.max():.2f}")

    # ---- 1b. step two: production and age (v1.2) ---------------------------------------------------
    rates = production_rates()
    fits, prow = production_fits(fitrows, rates)
    log(f"\nSTEP TWO (production adjusted to NHL terms; discounted by age in seasons 0-3)")
    log(f"  training rows: {len(prow):,} skater prospect-rows ({prow[['draftYear', 'pick']].drop_duplicates().shape[0]:,} "
        f"players); no production record {prow['no_record'].mean():.1%}")
    # GUARDS: each fit equals the look that measured it (when those outputs are on this machine)
    ac, nc = OUTPUT_DIR / "prospect_age_coefficients.csv", OUTPUT_DIR / "prospect_nhle_coefficients.csv"
    if ac.exists() and nc.exists():
        ac, nc = pd.read_csv(ac), pd.read_csv(nc)
        src = {("main", g): (ac, "+ age x production") for g in AGE_GROUPS}
        src.update({("main", "4+"): (nc, "production curved")})
        n_ok = 0
        for (v, g), (tab, arm) in src.items():
            cols, b, _ = fits[(v, g, "none")]
            ref = tab[(tab["k_group"] == g) & (tab["arm"] == arm)].iloc[0]
            gap = max(abs(b[i] - ref[c]) for i, c in enumerate(cols))
            assert gap < 1e-9, (v, g, arm, gap)
            n_ok += 1
        log(f"  guard: coefficients equal the production and age looks' for {n_ok} of {len(src)} fits (PASS)")
    for v in VERSIONS:
        for g in ("0", "1", "2", "3", "4+"):
            cols, b, se = fits[(v, g, "none")]
            log(f"  {v:<7} {g:>2}: " + "; ".join(f"{c} {b[i]:.3f} ({se[i]:.3f})" for i, c in enumerate(cols)))
    ep_ids = pd.read_sql("select draft_year draftYear, draft_overall pick, ep_player_id from ep_draft_selections",
                         sqlite3.connect(OUTPUT_DIR / "ep_out" / "ep_prospects.db"))
    EP_ID = {(int(a), int(b)): str(int(c)) for a, b, c in zip(ep_ids["draftYear"], ep_ids["pick"], ep_ids["ep_player_id"])
             if pd.notna(c)}

    def value_from(ep, birth, y, k, p_star, version, left_out="none"):
        """Value ($M) of a skater prospect at season y under one version of step two (None without an EP id or
        a birthdate). v1.3: keyed on the Elite Prospects id, so undrafted players (p_star 0) use it too."""
        if ep is None or pd.isna(birth):
            return None
        row = production_features(pd.DataFrame({"ep_player_id": [ep], "season": [y], "k": [k],
                                                "birthDate": [birth], "p_star": [p_star]}), rates).iloc[0]
        cols, b, _ = fits[(version, k_group(k), left_out)]
        return float(sum(b[i] * row[col] for i, col in enumerate(cols))), row

    def step_two(c, y, k, p_star, version, left_out="none"):
        """A drafted skater prospect: his EP id from the draft pages."""
        return value_from(EP_ID.get((int(c["draftYear"]), int(c["overallPickNumber"]))), c["birthDate"],
                          y, k, p_star, version, left_out)

    # ---- 2. drafted players and their NHL seasons --------------------------------------------------
    bacon = pd.read_csv(F["bacon"]).set_index("draft_pick")["p_star"]
    link = pd.read_csv(F["linkage"], parse_dates=["birthDate"])
    link["is_goalie"] = link["is_goalie"].astype(bool)
    link = link[link["link_status"] != "excluded_merged_name"].copy()
    link["key"] = link["playerName"].map(name_key)
    draft_day = {}
    for f in sorted((OUTPUT_DIR / "draft_raw").glob("draft_*.json")):
        rows = json.loads(f.read_text(encoding="utf-8"))["data"]
        draft_day[int(f.stem.split("_")[1])] = pd.Timestamp(min(r["draftDate"] for r in rows))
    tables = {False: season_table(F["WAR"], "Player"), True: season_table(F["GWAR"], "Goalie")}
    names_with_nhl = {}                                    # normalised name -> NHL start years (either table)
    for t in tables.values():
        for (n, y) in t.index:
            names_with_nhl.setdefault(n, set()).add(int(y))

    def seasons_of(row):
        tbl = tables[row["is_goalie"]]
        empty = pd.DataFrame({"GP": [], "WAR": []}, index=pd.Index([], name="start"))
        if pd.isna(row["war_names"]):
            return empty
        names = {norm(x) for x in str(row["war_names"]).split("|")} & set(tbl.index.get_level_values(0))
        if not names:
            return empty
        s = pd.concat([tbl.loc[n] for n in names]).groupby(level=0).sum()
        return s[s.index >= row["draftYear"]]             # GUARD (as pick_curve): no namesake's earlier seasons

    # ---- 3. the traded players ----------------------------------------------------------------------
    con = sqlite3.connect(F["trades"])
    a = pd.read_sql("select a.asset_id, a.trade_id, a.player_name, a.from_team, a.cap_hit_aav, a.is_ahl_jr, a.is_signing_rights, "
                    "l.acquiring_team, t.trade_date from trade_assets a join trades t using(trade_id) "
                    "join trade_legs l using(leg_id) where a.asset_type = 'player' and t.trade_date >= ?",
                    con, params=(TRADES_FROM,))
    a["date"] = pd.to_datetime(a["trade_date"])
    a["trade_season"] = np.where(a["date"].dt.month >= 7, a["date"].dt.year, a["date"].dt.year - 1)
    # v1.5 (Thomas, 2026-10-14): a trade after its season's last regular-season game is valued on the next page
    import trade_page as TP
    a["valuation_page"] = a["date"].map(TP.page)
    log(f"\nplayers traded from {TRADES_FROM}: {len(a)} assets "
        f"(trades.db ends {pd.read_sql('select max(trade_date) m from trades', con)['m'][0]})")

    # ---- 3a. who each traded player is: his NHL id from PuckPedia first, names second (v1.1) ------------
    pc, enc_c = CS.load_contracts()
    pt, enc_t = CS.load_trades()
    log(f"  PuckPedia contracts ({enc_c}) {len(pc):,} rows; PuckPedia trades ({enc_t}) {len(pt):,} rows "
        "(identity only: NHL ids for matching, no value input)")
    pc = pc.dropna(subset=["nhl_id", "cap_hit", "signing_date", "contract_end"]).copy()
    pc["key"] = (pc["first_name"].astype(str) + " " + pc["last_name"].astype(str)).map(name_key)
    pc["signed"] = CS.parse_export_dates(pc["signing_date"], "PuckPedia signing_date")   # v1.9: either date style
    pc["ends"] = pc["contract_end"].astype(str).str[-4:].astype(int).map(lambda y: pd.Timestamp(y, 6, 30))
    pt = pt[pt["player_id"].notna() & pt["nhl_id"].notna()].copy()
    pt["key"] = (pt["first_name"].astype(str) + " " + pt["last_name"].astype(str)).map(name_key)
    pt["date"] = CS.parse_export_dates(pt["trade_date"], "PuckPedia trade_date")         # v1.9: either date style
    pc_by, pt_by = dict(tuple(pc.groupby(pc["key"].str[0]))), dict(tuple(pt.groupby(pt["key"].str[0])))

    def first_ok(k1, k2):
        """Same surname is assumed; first names agree as canonical forms, or at least on the first letter."""
        return k1[1] == k2[1] or k1[1][:1] == k2[1][:1]

    def ids_for(r):
        """NHL ids for a traded asset: (1) a PuckPedia trade row of the same name within 3 days of the trade;
        (2) a PuckPedia contract of the same name whose cap hit equals the asset's and that runs on the trade
        date (signed on or before it, ending June 30 of its last season on or after it); (3, v1.4) when neither
        finds one, a PuckPedia contract of the same name running on the trade date, whatever its cap hit."""
        key, ids = name_key(r.player_name), {}
        t = pt_by.get(key[0])
        if t is not None:
            t = t[t["key"].map(lambda k: first_ok(k, key)) & ((t["date"] - r.date).abs() <= pd.Timedelta(days=3))]
            for i in t["nhl_id"].astype(int):
                ids.setdefault(i, set()).add("PuckPedia trade")
        c = pc_by.get(key[0])
        if c is not None and pd.notna(r.cap_hit_aav):
            c = c[c["key"].map(lambda k: first_ok(k, key)) & (c["cap_hit"].astype(float) == float(r.cap_hit_aav))
                  & (c["signed"] <= r.date) & (c["ends"] >= r.date)]
            for i in c["nhl_id"].astype(int):
                ids.setdefault(i, set()).add("PuckPedia contract")
        if not ids:
            # v1.4 (Thomas, 2026-10-14: "Fix it"): trades.db lists a player assigned to the AHL at $0, so the cap-hit
            # match finds nothing; a PuckPedia contract of the same name running on the trade date, any cap hit
            c = pc_by.get(key[0])
            if c is not None:
                # the SAME canonical first name, not just its first letter: without the cap hit as evidence, a
                # first-letter match took Vince Dunn's contract for Vincent Dunn (OTT 2013 #138) and Jordan
                # Greenway's for James Greenway (caught by the id-name guard, 2026-10-14)
                c = c[c["key"].map(lambda k: k == key) & (c["signed"] <= r.date) & (c["ends"] >= r.date)]
                for i in c["nhl_id"].astype(int):
                    ids.setdefault(i, set()).add("PuckPedia contract, any cap hit")
        return ids

    # the name tier's spellings: the linkage's name, and Elite Prospects' name for the same draft slot
    ep = sqlite3.connect(OUTPUT_DIR / "ep_out" / "ep_prospects.db")
    eps = pd.read_sql("select draft_year, draft_overall, player_name_ep from ep_draft_selections", ep)
    eps = eps.rename(columns={"draft_year": "draftYear", "draft_overall": "overallPickNumber"})
    link = link.merge(eps, on=["draftYear", "overallPickNumber"], how="left")
    link["key_ep"] = link["player_name_ep"].map(lambda n: name_key(n) if pd.notna(n) else None)
    link["pid"] = link["playerId"].map(lambda x: int(x) if pd.notna(x) else -1)

    def drafted_by(cands, date):
        held = cands["draftYear"].map(lambda y: draft_day.get(y, pd.Timestamp(y, 6, 26)) <= date).astype(bool)
        return cands.loc[held]

    def by_name(r):
        """v1.0's name tier, widened to Elite Prospects' spelling; returns (candidates, namesakes rejected)."""
        key = name_key(r.player_name)
        cand = drafted_by(link[(link["key"] == key) | (link["key_ep"] == key)], r.date)
        nhl_years = names_with_nhl.get(norm(r.player_name), set())
        # NAMESAKE GUARD: NHL seasons under this name between his draft and the trade would be his, but he has
        # none (zero_no_nhl_record), so the traded player is someone else. Seasons before his draft belong to
        # an older namesake and say nothing (Nathan Smith, drafted 2018, traded 2022).
        rejected = cand[(cand["link_status"] == "zero_no_nhl_record")
                        & cand["draftYear"].map(lambda dy: any(dy <= z < r.valuation_page for z in nhl_years))]
        return cand.drop(rejected.index), len(rejected)

    def show(c):
        return "; ".join(f"{x.draftYear} #{x.overallPickNumber}" for x in c.itertuples()) or "none"

    # ---- v1.3: undrafted players (Thomas, 2026-10-14: "NHL contracts only"; "Same model, no slot") ----------
    pc["bd"] = CS.parse_export_dates(pc["birthdate"], "PuckPedia birthdate")   # v1.9: either style; was m/d/Y with
    pc_by_id = dict(tuple(pc.groupby(pc["nhl_id"].astype(int))))              # errors="coerce", blank on Y-m-d
    PPINFO = {int(i): (g["bd"].iloc[0],
                       str(int(g["eliteprospects_id"].iloc[0])) if pd.notna(g["eliteprospects_id"].iloc[0]) else None,
                       str(g["position"].iloc[0]).startswith("G"))
              for i, g in pc_by_id.items()}

    def nhl_seasons_by_name(name, is_goalie):
        t = tables[is_goalie]
        n = norm(name)
        if n not in t.index.get_level_values(0):
            return pd.DataFrame({"GP": [], "WAR": []}, index=pd.Index([], name="start"))
        return t.loc[n]

    def undrafted(r, nid):
        """An undrafted player (or one drafted before 2005): NHL rights only through an NHL contract, i.e. a cap
        hit without trades.db's AHL/junior flag, or a PuckPedia contract of his running on the trade date. With
        one, he is valued by the drafted model with the slot term at zero, seasons counted from his first
        draft-eligible year (the first draft at which he was 18 by September 15)."""
        if nid is None:
            # trades.db lists a player assigned to the AHL at $0, so the cap-hit match finds no contract: look for a
            # PuckPedia contract of the same name running on the trade date, whatever its cap hit (one id only)
            key = name_key(r.player_name)
            c_ = pc_by.get(key[0])
            if c_ is not None:
                c_ = c_[c_["key"].map(lambda k_: k_ == key) & (c_["signed"] <= r.date) & (c_["ends"] >= r.date)]
                found = set(c_["nhl_id"].astype(int))
                if len(found) == 1:
                    nid = found.pop()
        running = nid is not None and nid in pc_by_id and bool(
            ((pc_by_id[nid]["signed"] <= r.date) & (pc_by_id[nid]["ends"] >= r.date)).any())
        nhl_contract = (pd.notna(r.cap_hit_aav) and r.cap_hit_aav > 0 and not r.is_ahl_jr) or running
        birth, ep, gk = PPINFO.get(nid, (pd.NaT, None, None)) if nid is not None else (pd.NaT, None, None)
        if gk is None:                                 # no PuckPedia record: the table his name appears in
            gk = norm(r.player_name) not in tables[False].index.get_level_values(0) and \
                norm(r.player_name) in tables[True].index.get_level_values(0)
        s = nhl_seasons_by_name(r.player_name, gk)
        y = int(r.valuation_page)
        out = {"drafted_match": "none", "undrafted_nhl_contract": nhl_contract, "is_goalie": gk}
        if not is_prospect(s, y, gk):
            out["status"] = "undrafted or pre-2005: player model (not a prospect)"
            return out
        out["nhl_id_undrafted"] = nid
        if not nhl_contract:
            if r.date < PP_FROM:
                # PuckPedia holds contracts running in 2018-19 or later; one that ended earlier cannot be seen
                out["status"] = "undrafted, contract not seen (traded before PuckPedia's coverage: not valued)"
            elif r.is_signing_rights:
                out["status"] = "undrafted, signing rights only (contract expired: worth zero)"
                out["value_M"] = out["value_slot_only_M"] = 0.0
            else:
                out["status"] = "undrafted, no NHL contract (no NHL rights: worth zero)"
                out["value_M"] = out["value_slot_only_M"] = 0.0
            return out
        if pd.isna(birth):
            out["status"] = "undrafted, NHL contract, not valued (no PuckPedia record: no birthdate or EP id)"
            return out
        first_elig = birth.year + (18 if (birth.month, birth.day) <= (9, 15) else 19)
        k = max(y - first_elig, 0)
        end = window_end(birth, gk, s)
        out.update({"birthDate": birth, "first_eligible_draft": first_elig, "valuation_season": y,
                    "seasons_since_draft": k, "k_group": k_group(k), "window_end": end, "p_star": 0.0,
                    "nhl_games_before": float(s.loc[s.index < y, "GP"].sum())})
        if y >= end:
            out["status"] = "undrafted prospect, club control over (worth zero)"
            out["value_M"] = out["value_slot_only_M"] = 0.0
            return out
        out["value_slot_only_M"] = 0.0                 # no slot
        two = None if gk else value_from(ep, birth, y, k, 0.0, "main")
        if two is None:
            out["status"] = ("undrafted prospect, valued (goalie: slot alone, so zero)" if gk
                             else "undrafted prospect, valued (no EP id: zero)")
            out["value_M"] = out["value_own_draft_out_M"] = 0.0
            out["value_basis"] = "slot alone (goalie)" if gk else "no production record"
            return out
        out["status"] = "undrafted prospect, valued (NHL contract)"
        out["value_M"], row = two
        out["value_own_draft_out_M"] = out["value_M"]          # no draft in the fit to leave out
        out.update({"value_basis": "production (undrafted, slot at zero)", "nhle82": row["nhle82"],
                    "n_prod_seasons": int(row["n_prod_seasons"]), "past_elig": row["past_elig"]})
        return out

    sv_main = main_sv["star_value_M"].to_dict()
    sv_out = {(r.k_group, int(r.left_out)): r.star_value_M for r in sv[sv["left_out"] != "none"].itertuples()}
    out = []
    for r in a.itertuples():
        ids = ids_for(r)
        name_cand, n_rej = by_name(r)
        rec = {"asset_id": r.asset_id, "trade_id": r.trade_id, "trade_date": r.trade_date,
               "trade_season": r.trade_season, "valuation_page": r.valuation_page,
               "player_name": r.player_name, "from_team": r.from_team,
               "acquiring_team": r.acquiring_team, "cap_hit": r.cap_hit_aav, "is_ahl_jr": bool(r.is_ahl_jr),
               "is_signing_rights": bool(r.is_signing_rights), "namesakes_rejected": n_rej,
               "by_name": show(name_cand)}
        if len(ids) == 1:
            nid, src = next(iter(ids.items()))
            cand = drafted_by(link[link["pid"] == nid], r.date)
            if len(cand) > 1:                         # drafted twice: the later draft holds the rights
                cand = cand[cand["draftYear"] == cand["draftYear"].max()]
            rec.update({"nhl_id": nid, "match": "NHL id (" + " + ".join(sorted(src)) + ")", "by_id": show(cand)})
            rec["id_and_name_agree"] = rec["by_id"] == rec["by_name"]
        else:
            cand = name_cand
            rec["match"] = "name" if not ids else "name (PuckPedia ids conflict: " + ", ".join(map(str, ids)) + ")"
        if len(cand) == 0:
            rec["status"] = ("not drafted 2005-2026 (by NHL id)" if len(ids) == 1
                             else "no drafted match (undrafted, drafted before 2005, or name not found)")
            rec.update(undrafted(r, next(iter(ids)) if len(ids) == 1 else None))
            out.append(rec)
            continue
        if len(cand) > 1:
            rec["status"] = "ambiguous name (not valued)"
            rec["candidates"] = show(cand)
            out.append(rec)
            continue
        c = cand.iloc[0]
        s = seasons_of(c)
        y = max(int(r.valuation_page), int(c["draftYear"]))
        k = y - int(c["draftYear"])
        slot = int(c["overallPickNumber"])
        p_star = float(bacon[min(slot, int(bacon.index.max()))])   # picks past 225 (2005 only): the last slot's chance
        end = window_end(c["birthDate"], c["is_goalie"], s) if pd.notna(c["birthDate"]) else None
        rec.update({"draftYear": int(c["draftYear"]), "pick": slot, "drafted_name": c["playerName"],
                    "position": c["position"], "is_goalie": bool(c["is_goalie"]), "link_status": c["link_status"],
                    "valuation_season": y, "seasons_since_draft": k, "k_group": k_group(k),
                    "nhl_games_before": float(s.loc[s.index < y, "GP"].sum()), "window_end": end,
                    "p_star": p_star})
        if not is_prospect(s, y, bool(c["is_goalie"])):
            rec["status"] = "player model (not a prospect)"
        elif end is not None and y >= end:
            rec["status"] = "prospect, club control over (worth zero)"
            rec["value_M"] = rec["value_slot_only_M"] = 0.0
        else:
            rec["status"] = "prospect, valued"
            rec["star_value_M"] = sv_main[k_group(k)]
            own = int(c["draftYear"]) if int(c["draftYear"]) in FIT_CLASSES else "none"   # his draft in the fit?
            # step one, the slot alone (v1.0-v1.1's value; goalies keep it as their value)
            rec["value_slot_only_M"] = p_star * sv_main[k_group(k)]
            slot_out = p_star * sv_out[(k_group(k), own)] if own != "none" else rec["value_slot_only_M"]
            two = None if bool(c["is_goalie"]) else step_two(c, y, k, p_star, "main")
            if two is None:                           # goalies (and a skater without an EP id): the slot alone
                rec["value_M"] = rec["value_slot_only_M"]
                rec["value_own_draft_out_M"] = slot_out
                rec["value_basis"] = "slot alone (goalie)" if bool(c["is_goalie"]) else "slot alone (no EP id)"
            else:
                rec["value_M"], row = two
                rec["value_own_draft_out_M"] = step_two(c, y, k, p_star, "main", own)[0]
                rec.update({"value_basis": "slot + production" if k_group(k) in SLOT_GROUPS else "production",
                            "nhle82": row["nhle82"], "n_prod_seasons": int(row["n_prod_seasons"]),
                            "past_elig": row["past_elig"]})
            if end is None:
                rec["status"] = "prospect, valued (no birthdate: control window not checked)"
        out.append(rec)
    v = pd.DataFrame(out)

    # ---- 4. report ----------------------------------------------------------------------------------
    log("\nHOW EACH TRADED PLAYER WAS TREATED")
    log(v.groupby("status").agg(assets=("asset_id", "size"), value_M=("value_M", "sum")).round(2).to_string())
    log(f"  namesakes rejected by the guard: {int(v['namesakes_rejected'].sum())} candidate rows")
    amb = v[v["status"].str.startswith("ambiguous")]
    for r in amb.itertuples():
        log(f"  ambiguous: {r.player_name} ({r.trade_date}): {r.candidates}")
    pv = v[v["status"].str.startswith("prospect, valued")]
    # v1.3: the undrafted players
    ud = v[v["drafted_match"].eq("none")]
    log(f"\nUNDRAFTED (or drafted before 2005): {len(ud)} assets")
    log(ud.groupby("status").agg(assets=("asset_id", "size"), value_M=("value_M", "sum")).round(2).to_string())
    uv = ud[ud["status"].str.startswith("undrafted prospect")]
    for r in uv.sort_values("trade_date").itertuples():
        log(f"    {r.trade_date}  {r.player_name:<22} born {r.birthDate:%Y-%m-%d}, first eligible {int(r.first_eligible_draft)}, "
            f"k={int(r.seasons_since_draft)}, control ends {int(r.window_end)}: ${r.value_M:5.2f}M; production {r.nhle82 if pd.notna(r.nhle82) else float('nan'):.1f} per 82; "
            f"{r.status}")
    allv = v[v["status"].str.startswith(("prospect, valued", "undrafted prospect, valued"))]
    log(f"  all prospects valued (drafted and undrafted): {len(allv)} assets, ${allv['value_M'].sum():,.2f}M")

    log(f"\nPROSPECTS VALUED: {len(pv)} assets, {pv['player_name'].nunique()} players, total ${pv['value_M'].sum():,.1f}M "
        f"(own draft left out: ${pv['value_own_draft_out_M'].sum():,.1f}M)")
    log(pv.groupby("k_group").agg(assets=("asset_id", "size"), mean_M=("value_M", "mean"),
                                  total_M=("value_M", "sum")).round(2).to_string())
    log(f"  beyond the fitted seasons (k > {K_MAX}, valued at the 4+ star value): {int((pv['seasons_since_draft'] > K_MAX).sum())}")
    log(f"  with 1-9 NHL games before the valuation season: {int((pv['nhl_games_before'] > 0).sum())}; "
        f"flagged signing rights: {int(pv['is_signing_rights'].sum())}; flagged AHL/junior: {int(pv['is_ahl_jr'].sum())}")
    log(f"  inside the fit's drafts (2007-2017; the stated overlap): {int(pv['draftYear'].isin(FIT_CLASSES).sum())}")
    log("  basis: " + ", ".join(f"{k_} {n_}" for k_, n_ in pv["value_basis"].value_counts().items()))
    log(f"  below zero (a remaining surplus can be negative; kept, as the pick curve keeps negative careers): "
        f"{int((pv['value_M'] < 0).sum())}, total ${pv.loc[pv['value_M'] < 0, 'value_M'].sum():.2f}M")

    log(f"\nTWO VERSIONS SIDE BY SIDE ($M; the same {len(pv)} assets)")
    for col, lab in (("value_M", "adopted: slot + production, discounted by age"),
                     ("value_slot_only_M", "step one: the slot alone")):
        log(f"  {lab:<46} total {pv[col].sum():7.2f}; mean {pv[col].mean():.3f}; largest {pv[col].max():.2f}")
    diff = pv["value_M"] - pv["value_slot_only_M"]
    log(f"  {'production and age (adopted minus slot alone)':<46} total {diff.sum():+7.2f}; moved by $0.25M or more: "
        f"{int((diff.abs() >= 0.25).sum())} of {len(pv)}; largest {diff.abs().max():.2f}; rank correlation "
        f"{pv['value_M'].rank().corr(pv['value_slot_only_M'].rank()):.3f}")

    log("\n  the twenty most valuable (beside: slot alone, own draft left out):")
    for r in pv.sort_values("value_M", ascending=False).head(20).itertuples():
        log(f"    {r.trade_date}  {r.player_name:<24} {int(r.draftYear)} #{int(r.pick):<3} k={int(r.seasons_since_draft)}  "
            f"${r.value_M:5.2f}M  (slot ${r.value_slot_only_M:5.2f}M, "
            f"own draft out ${r.value_own_draft_out_M:5.2f}M)  to {r.acquiring_team}")
    log("\nWHO EACH TRADED PLAYER IS (v1.1: NHL id from PuckPedia first, names second)")
    log(v["match"].map(lambda m: m if not m.startswith("name (") else "name (PuckPedia ids conflict)")
        .value_counts().to_string())
    idm = v[v["match"].str.startswith("NHL id")]
    dis = idm[~idm["id_and_name_agree"].astype(bool)]
    log(f"  matched by NHL id: {len(idm)}; the name rules give the same draftee for {len(idm) - len(dis)}, "
        f"a different answer for {len(dis)}:")
    for r in dis.itertuples():
        log(f"    {r.trade_date} {r.player_name:<24} by id: {r.by_id:<14} by name: {r.by_name:<14} -> {r.status}")
    # GUARD: every disagreement has been read and the NHL id found right; a new one stops the run for review
    unreviewed = set(zip(dis["trade_date"], dis["player_name"])) - REVIEWED_DISAGREEMENTS
    assert not unreviewed, f"id and name disagree on unreviewed assets: {sorted(unreviewed)}"
    log(f"  guard: all {len(dis)} disagreements were reviewed (the NHL id is right in each) (PASS)")
    nd = v[v["drafted_match"].eq("none") & ~v["match"].str.startswith("NHL id")]   # v1.3: by name, no draftee
    log(f"\n  not matched to a drafted player: {len(nd)} assets, of them flagged AHL/junior {int(nd['is_ahl_jr'].sum())}, "
        f"signing rights {int(nd['is_signing_rights'].sum())}, with NHL seasons in the WAR tables "
        f"{int(nd['player_name'].map(lambda n: norm(n) in names_with_nhl).sum())}")
    nn = nd[~nd["player_name"].map(lambda n: norm(n) in names_with_nhl)]
    log(f"  of them with no NHL season under the name (undrafted, or names not found): "
        + ", ".join(sorted(nn["player_name"].unique())))
    rj = v[v["namesakes_rejected"] > 0]
    for r in rj.itertuples():
        log(f"  namesake guard: {r.player_name} ({r.trade_date}) -> {r.status}")
    co = v[v["status"].str.startswith("prospect, club control over")]   # drafted (undrafted listed above)
    log(f"  past club control (worth zero): " + "; ".join(
        f"{r.player_name} ({int(r.draftYear)} #{int(r.pick)}, control ended {int(r.window_end)})" for r in co.itertuples()))

    v.drop(columns=[c for c in ("date",) if c in v.columns]).to_csv(OUTPUT_DIR / "prospect_values.csv", index=False)
    sv.to_csv(OUTPUT_DIR / "prospect_star_values.csv", index=False)
    pd.DataFrame([{"version": v_, "k_group": g_, "left_out": lo_, **{c_: b_[i] for i, c_ in enumerate(cols_)}}
                  for (v_, g_, lo_), (cols_, b_, _) in fits.items()]).to_csv(
        OUTPUT_DIR / "prospect_production_fits.csv", index=False)
    (OUTPUT_DIR / "prospect_values_log.txt").write_text("\n".join(LOG), encoding="utf-8")
    log(f"\nwrote prospect_values.csv, prospect_star_values.csv, prospect_production_fits.csv, prospect_values_log.txt "
        f"in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
