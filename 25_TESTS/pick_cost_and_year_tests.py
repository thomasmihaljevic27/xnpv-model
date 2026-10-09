"""
pick_cost_and_year_tests.py -- the remaining skater tests on the adopted pick curve.

THE ADOPTED CURVE (MODEL_DIRECTIVES.md directive 6, Thomas 2026-10-09)
  surplus = b x Bacon's star chance for the slot, through zero, draft-year
  indicators (sum to zero), read at the average draft year; b = $31.37M on the
  first look's surplus (pick_regression_first_look.py v1.1).

PART 1 -- COST AND DEFINITION VARIANTS (each changes what a player's surplus
IS, so they are compared by how far they move the curve, never by held-out
miss against the main version: the targets differ). Thomas: keep the cost
side's alternatives.
  main         as the first look: entry-level maximum, then the qualifying-offer
               chain; a season under 10 NHL games does not use up an entry-level
               year, at any age (a proxy for the slide).
  slides_cba   CBA 9.1(d): only an 18- or 19-year-old's season under 10 NHL games
               slides (age on September 15 of that season); from 20, every season
               from his first NHL season uses up a year. (The 9.1(d) exception for a
               player turning 20 between September 16 and December 31 is ignored.)
  no_slides    every season from his first NHL season uses up a year, any age.
  floor_zero   main, each player's total surplus floored at zero (a club is not
               charged for a career that cost more than it returned).
  arbitration  main, but once he is eligible for salary arbitration (CBA 12.1:
               first-contract age 18-20 needs 4 years of professional experience,
               21 needs 3, 22-23 need 2, 24+ needs 1), each later control season
               is costed at the market price of what he delivered, so it carries
               no surplus. PROXIES: signing age = age on September 15 of his first
               NHL season (as for the entry-level length); a year of experience =
               a season of 10+ NHL games (the CBA also counts 10+ professional
               games at 20+, e.g. the AHL, which the data lacks, so eligibility is
               reached later here and the cut is conservative).
  Reported for each: the scale b, the change against main, values at key picks.

PART 2 -- DOES THE SCALE DIFFER BY DRAFT YEAR? (main surplus; same target, so
an inference test is fair). Fits one scale per class (b_c x star chance, year
levels kept), a robust (HC1) Wald test that all eleven are equal, each class's
scale with its standard error, and the spread of the class scales against the
spread sampling noise alone would give. The meeting agreed that year-to-year
change in the slope is accepted as uncertainty; this measures how much.

TRAILING WEIGHTING CHECK (directive 6): nothing reads a trailing total.

INPUTS: as pick_regression_first_look.py v1.1 (linkage, windows, WAR) plus its
players file (reproduction guard) and SOURCE_DIR/draft_slot_baseline.csv.

Run from the repo root:  python 25_TESTS/pick_cost_and_year_tests.py
"""

import os
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv

SCRIPT_VERSION = "pick_cost_and_year_tests.py v1.0 (2026-10-09)"
load_dotenv()
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
import skater_forward_projection as sfp          # noqa: E402
import rfa_terminal_value as rtv                 # noqa: E402

SOURCE_DIR, OUTPUT_DIR = Path(os.environ["SOURCE_DIR"]), Path(os.environ["OUTPUT_DIR"])
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


log(SCRIPT_VERSION)
F = {"linkage": OUTPUT_DIR / "draft_pick_linkage.csv", "windows": OUTPUT_DIR / "draft_window_count.csv",
     "WAR": SOURCE_DIR / "WAR.csv", "first_look": OUTPUT_DIR / "pick_first_look_players.csv",
     "fl_log": OUTPUT_DIR / "pick_first_look_log.txt", "bacon": SOURCE_DIR / "draft_slot_baseline.csv"}
for k, p in F.items():
    log(f"  input {k}: {p.resolve()}  (modified {pd.Timestamp(p.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M})")
assert F["fl_log"].read_text(encoding="utf-8").startswith("pick_regression_first_look.py v1.1")

# ---- constants: identical to pick_regression_first_look.py v1.1 -------------------------
ALPHA, BETA_F, BETA_D, GAMMA, LINE = sfp.price_constants()
CAP = {2007: 50.3e6, 2008: 56.7e6, 2009: 56.8e6, 2010: 59.4e6, 2011: 64.3e6, 2012: 60.0e6, 2013: 64.3e6,
       2014: 69.0e6, **{y: sfp.CAP_CEILING[y] for y in range(2015, 2026)}}
LMIN = {2007: 475_000, 2008: 475_000, 2009: 500_000, 2010: 500_000, 2011: 525_000, 2012: 525_000,
        2013: 550_000, 2014: 550_000, **{y: sfp.league_min_path(y) for y in range(2015, 2026)}}
ELC_MAX = {**{y: 875_000 for y in (2007, 2008)}, **{y: 900_000 for y in (2009, 2010)},
           **{y: 925_000 for y in range(2011, 2018)}}
SHORT = {2012: 82 / 48, 2019: 82 / 70, 2020: 82 / 56}
CAP_NOW, CAMEO_GP, LAST_START = sfp.CAP_CEILING[2025], 10, 2025
ARB_YEARS = lambda age: 4 if age <= 20 else 3 if age == 21 else 2 if age <= 23 else 1   # CBA 12.1(a)


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z ]", "", s.lower()).strip()


link = pd.read_csv(F["linkage"], parse_dates=["birthDate"])
win = pd.read_csv(F["windows"])
fl = pd.read_csv(F["first_look"])
p = link[link["draftYear"].between(2007, 2017) & ~link["is_goalie"].astype(bool)].merge(
    win[["draftYear", "overall", "end_g3"]], left_on=["draftYear", "overallPickNumber"],
    right_on=["draftYear", "overall"], validate="one_to_one")
p = p[p["end_g3"].notna() & (p["link_status"] != "excluded_merged_name")]
p = p.merge(fl[["draftYear", "pick", "surplus"]], left_on=["draftYear", "overallPickNumber"],
            right_on=["draftYear", "pick"], validate="one_to_one")

war = pd.read_csv(F["WAR"], usecols=["Player", "Season", "GP", "WAR"])
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
    return s[s.index >= row["draftYear"]]


def age_on(row, y):
    return int((pd.Timestamp(y, 9, 15) - row["birthDate"]).days / 365.25) if pd.notna(row["birthDate"]) else 19


def surplus(row, variant):
    """A player's summed surplus (cap shares) under one variant."""
    s = seasons_of(row)
    beta = BETA_D if row["position"] == "D" else BETA_F
    last = min(int(row["end_g3"]) - 1, LAST_START)
    played = s[(s["GP"] > 0) & (s.index <= last)]
    if played.empty:
        return 0.0
    first = int(played.index.min())
    sign_age = age_on(row, first)
    n_elc = 3 if sign_age <= 21 else 2 if sign_age <= 23 else 1
    arb_need = ARB_YEARS(sign_age)
    elc_done, prior, pro_years, tot = 0, None, 0, 0.0
    for y in range(int(row["draftYear"]), last + 1):
        gp = float(s.loc[y, "GP"]) if y in s.index else 0.0
        wins = float(s.loc[y, "WAR"]) * SHORT.get(y, 1.0) if y in s.index else 0.0
        if variant in ("no_slides", "slides_cba") and y >= first:
            in_elc = elc_done < n_elc                 # the deal runs by calendar from his first NHL season
        else:
            in_elc = elc_done < n_elc and gp > 0
        if not in_elc and elc_done >= n_elc:
            prior = rtv.qualifying_offer(prior or ELC_MAX[row["draftYear"]], prior or ELC_MAX[row["draftYear"]],
                                         y, False)
        arb = variant == "arbitration" and not in_elc and pro_years >= arb_need
        if gp >= CAMEO_GP:
            pro_years += 1                            # counted after this season's cost is set
        burn = in_elc and (
            gp >= CAMEO_GP if variant in ("main", "floor_zero", "arbitration") else
            True if variant == "no_slides" else
            (gp >= CAMEO_GP or age_on(row, y) >= 20))  # slides_cba: only 18/19-year-olds slide
        if burn:
            elc_done += 1
        if gp == 0:
            continue
        scale = gp / 82 if gp < CAMEO_GP else 1.0
        value = max(ALPHA + beta * wins + GAMMA * 1, LMIN[y] / CAP[y]) * scale
        cost = value if arb else (ELC_MAX[row["draftYear"]] if in_elc else prior) / CAP[y] * scale
        tot += value - cost
    return max(tot, 0.0) if variant == "floor_zero" else tot


VARIANTS = ["main", "slides_cba", "no_slides", "floor_zero", "arbitration"]
for v in VARIANTS:
    p[v] = p.apply(lambda r: surplus(r, v), axis=1) * CAP_NOW / 1e6
bad = (p["main"] * 1e6 - p["surplus"]).abs() > 1.0
assert not bad.any(), p.loc[bad, ["playerName", "main", "surplus"]]   # reproduction guard
log(f"  reproduction guard: main equals the first look for all {len(p):,} skater picks")

bacon = pd.read_csv(F["bacon"]).set_index("draft_pick")["p_star"]
p["p_star"] = p["overallPickNumber"].map(bacon)
CL = sorted(p["draftYear"].unique())


def year_cols(years):
    X = np.zeros((len(years), len(CL) - 1))
    for j, c in enumerate(CL[:-1]):
        X[:, j] = (years == c)
    X[years == CL[-1], :] = -1.0
    return X


Y = year_cols(p["draftYear"].values)


def scale(y):
    m = sm.OLS(y, np.column_stack([p["p_star"].values, Y])).fit(cov_type="HC1")
    return m.params[0], m.bse[0]


# ---- part 1 ---------------------------------------------------------------------------------
log("\nPART 1: COST AND DEFINITION VARIANTS ($M; scale = $ per 100% star chance; skaters 2007-2017)")
b0, _ = scale(p["main"].values)
at = [1, 5, 10, 20, 32, 64, 100]
rows = []
for v in VARIANTS:
    b, se = scale(p[v].values)
    rows.append({"variant": v, "mean surplus": p[v].mean(), "picks changed": int((p[v] - p["main"]).abs().gt(1e-6).sum()),
                 "scale": b, "se": se, "vs main %": 100 * (b / b0 - 1),
                 **{f"#{k}": b * bacon[k] for k in at}})
log(pd.DataFrame(rows).round(2).to_string(index=False))

# ---- part 2 ---------------------------------------------------------------------------------
log("\nPART 2: DOES THE SCALE DIFFER BY DRAFT YEAR? (main surplus)")
yrs = p["draftYear"].values
Xc = np.column_stack([p["p_star"].values * (yrs == c) for c in CL] + [Y])
m = sm.OLS(p["main"].values, Xc).fit(cov_type="HC1")
R = np.zeros((len(CL) - 1, Xc.shape[1]))
for j in range(len(CL) - 1):
    R[j, j], R[j, len(CL) - 1] = 1, -1                # each class's scale equals 2017's
w = m.wald_test(R, scalar=True)
log(f"  Wald test, all eleven class scales equal: chi2 {float(w.statistic):.1f} on {len(CL) - 1} df, "
    f"p = {float(w.pvalue):.4f}")
bc, sec = m.params[:len(CL)], m.bse[:len(CL)]
tab = pd.DataFrame({"class": CL, "scale": bc, "se": sec, "#1": bc * bacon[1], "#10": bc * bacon[10],
                    "#32": bc * bacon[32]})
log(tab.round(2).to_string(index=False))
spread = np.std(bc, ddof=1)
noise = np.sqrt(np.mean(sec ** 2))
true_sd = np.sqrt(max(spread ** 2 - noise ** 2, 0.0))
log(f"  spread of class scales (sd) {spread:.2f}; typical sampling error {noise:.2f}; "
    f"spread beyond sampling noise {true_sd:.2f} ({100 * true_sd / b0:.0f}% of the pooled {b0:.2f})")
log(f"  largest classes: " + ", ".join(f"{c} {x:.1f}" for c, x in sorted(zip(CL, bc), key=lambda t: -t[1])[:3]))

p[["draftYear", "overallPickNumber", "playerName", "p_star"] + VARIANTS].to_csv(
    OUTPUT_DIR / "pick_cost_and_year_tests.csv", index=False)
(OUTPUT_DIR / "pick_cost_and_year_tests_log.txt").write_text("\n".join(LOG), encoding="utf-8")
log(f"\nwrote pick_cost_and_year_tests.csv and its log in {OUTPUT_DIR}")
