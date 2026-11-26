"""
pick_elc_term_check.py -- what pricing a drafted player's entry-level seasons at the term left on the deal would do.

QUESTION (the pick document's choices table, 2026-11-26; Thomas: "re-run those two"): pick_curve.py prices every
delivered season at one year of term. The alternative prices each entry-level season at the term left on the
entry-level deal (3, 2, 1 for a three-year deal), as a contract season is priced in the player model. This script
measures what that alternative does to each pick's NPV over club control and to the star value, on the pick curve as
it runs today.

HOW
  * Each drafted player's entry-level window is rebuilt as pick_curve.py v1.12 builds it: his first NHL season, and
    3 / 2 / 1 seasons by his CBA age (rfa_terminal_value.cba_age) on September 15 of the year he signed
    (elc_signing_dates.csv), his first NHL season standing in without a date. GUARD: the rebuilt window equals the
    `in_entry_level` flag of every priced season in pick_curve_seasons.csv.
  * Each entry-level season's value is recomputed on the line pick_curve.py uses (skaters: price_constants(),
    the defence slope for D; goaltenders: contract_npv.goalie_line) at one year of term. GUARD: it equals the stored
    value_share to 1e-12. Then it is priced at the term left, floored at the league minimum, scaled for a call-up.
  * Each pick's NPV over club control changes by the difference, restated at the 2025-26 cap; lapsed rights stay
    zero. The star value is refitted as pick_curve.py fits it (through zero, no draft-year terms, robust errors, the
    drafted players who died left out). GUARD: the unchanged fit reproduces pick_curve_scales.csv's main star value.

INPUTS: OUTPUT_DIR/pick_curve_players.csv, pick_curve_seasons.csv, pick_curve_scales.csv, draft_pick_linkage.csv,
elc_signing_dates.csv.  OUTPUT: printed (save with Tee to OUTPUT_DIR/pick_elc_term_check_log.txt).
Run from the repo root:  python 25_TESTS/pick_elc_term_check.py
"""

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv

SCRIPT_VERSION = "pick_elc_term_check.py v1.0 (2026-11-26)"
load_dotenv(".env")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
import skater_forward_projection as sfp   # noqa: E402
import rfa_terminal_value as rtv          # noqa: E402
import contract_npv as cnpv               # noqa: E402

OUT = Path(os.environ["OUTPUT_DIR"])
print(SCRIPT_VERSION)
F = {k: OUT / f"{k}.csv" for k in ("pick_curve_players", "pick_curve_seasons", "pick_curve_scales",
                                   "draft_pick_linkage", "elc_signing_dates")}
for k, p in F.items():
    print(f"  input {k}: {p.resolve()}  (modified {pd.Timestamp(p.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M})")

# pick_curve.py's constants (copied from v1.12; the guards below fail if they differ from what it priced on)
ALPHA, BETA_F, BETA_D, GAMMA, LINE = sfp.price_constants()
CAP = {2007: 50.3e6, 2008: 56.7e6, 2009: 56.8e6, 2010: 59.4e6, 2011: 64.3e6, 2012: 60.0e6, 2013: 64.3e6,
       2014: 69.0e6, **{y: sfp.CAP_CEILING[y] for y in range(2015, 2026)}}
LMIN = {2007: 475_000, 2008: 475_000, 2009: 500_000, 2010: 500_000, 2011: 525_000, 2012: 525_000,
        2013: 550_000, 2014: 550_000, **{y: sfp.league_min_path(y) for y in range(2015, 2026)}}
CAP_NOW = sfp.CAP_CEILING[2025]

pl = pd.read_csv(F["pick_curve_players"])
se = pd.read_csv(F["pick_curve_seasons"])
main = float(pd.read_csv(F["pick_curve_scales"]).set_index("scale_kind").loc["main", "scale_M"])
link = pd.read_csv(F["draft_pick_linkage"], parse_dates=["birthDate"])
birth = {(int(a), int(b)): d for a, b, d in zip(link["draftYear"], link["overallPickNumber"], link["birthDate"])}
el = pd.read_csv(F["elc_signing_dates"]).dropna(subset=["draftYear", "signing_year"])
signed = {(int(a), int(b)): int(c) for a, b, c in zip(el["draftYear"], el["pick"], el["signing_year"])}
info = pl.set_index(["draftYear", "pick"])[["position", "is_goalie"]]


def fit(frame, col):
    frame = frame[~frame["excluded_deceased"].astype(bool)]
    m = sm.OLS(frame[col].values / 1e6, frame[["p_star"]].values).fit(cov_type="HC1")
    return float(m.params[0]), float(m.bse[0])


b0, s0 = fit(pl, "surplus")
assert abs(b0 - main) < 1e-9, (b0, main)
print(f"\nguard: the fit reproduces the main star value, ${b0:.4f}M")

# the entry-level window, rebuilt
first = se.groupby(["draftYear", "pick"])["season"].min()
n_elc = {}
for key, f0 in first.items():
    age = rtv.cba_age(birth[key], signed.get(key, int(f0)))
    n_elc[key] = 3 if age <= 21 else 2 if age <= 23 else 1
k_ = list(zip(se["draftYear"], se["pick"]))
se["first"] = [first[k] for k in k_]
se["n_elc"] = [n_elc[k] for k in k_]
rebuilt = (se["season"] >= se["first"]) & (se["season"] < se["first"] + se["n_elc"])
bad = int((rebuilt != se["in_entry_level"].astype(bool)).sum())
assert bad == 0, f"{bad} seasons' entry-level flag differs from the rebuilt window"
print(f"guard: the rebuilt entry-level window equals pick_curve's flag on all {len(se):,} priced seasons")

# each entry-level season, at one year of term (guard) and at the term left
e = se[se["in_entry_level"].astype(bool)].copy()
e["term_left"] = e["first"] + e["n_elc"] - e["season"]
gk = [bool(info.loc[k, "is_goalie"]) for k in zip(e["draftYear"], e["pick"])]
dk = [info.loc[k, "position"] == "D" for k in zip(e["draftYear"], e["pick"])]
floor = np.array([LMIN[y] / CAP[y] for y in e["season"]])


def raw(w, t, g, d):
    return cnpv.goalie_line(w, t) if g else ALPHA + (BETA_D if d else BETA_F) * w + GAMMA * t


v1 = np.array([max(raw(w, 1, g, d), f) * s for w, g, d, f, s in zip(e["war_82"], gk, dk, floor, e["games_scale"])])
gap = float(np.max(np.abs(v1 - e["value_share"].to_numpy())))
assert gap < 1e-12, gap
print(f"guard: one-year pricing reproduces every entry-level season's stored value (largest gap {gap:.1e})")
vt = np.array([max(raw(w, t, g, d), f) * s for w, t, g, d, f, s in
               zip(e["war_82"], e["term_left"], gk, dk, floor, e["games_scale"])])
e["delta_share"] = vt - e["value_share"].to_numpy()
add = e.groupby(["draftYear", "pick"])["delta_share"].sum() * CAP_NOW
pl["delta"] = [add.get(k, 0.0) for k in zip(pl["draftYear"], pl["pick"])]
pl["surplus_term_left"] = np.where(pl["surplus"] == 0.0, 0.0, pl["surplus"] + pl["delta"])   # lapsed rights stay zero

played3 = e[e["n_elc"] == 3].groupby(["draftYear", "pick"]).agg(n=("season", "size"), d=("delta_share", "sum"))
full3 = played3[played3["n"] == 3]
print(f"\nentry-level seasons priced: {len(e):,} (term left 3: {(e['term_left'] == 3).sum():,}, 2: "
      f"{(e['term_left'] == 2).sum():,}, 1: {(e['term_left'] == 1).sum():,})")
print(f"  a three-year deal played in full, above the floor each season: + 3 x term premium = "
      f"{100 * 3 * GAMMA:.2f}% of the cap (skater line, {GAMMA:.10f} a year)")
print(f"  players who played all three seasons of a three-year deal: {len(full3):,}; mean addition "
      f"{100 * full3['d'].mean():.2f}% of the cap, largest {100 * full3['d'].max():.2f}%")
print(f"  added to NPV over club control, all picks: ${pl['delta'].sum() / 1e6:,.1f}M "
      f"(of ${pl['surplus'].sum() / 1e6:,.1f}M)")
b1, s1 = fit(pl, "surplus_term_left")
print(f"\nSTAR VALUE ($M at the 2025-26 cap): one year of term {b0:.4f} (se {s0:.2f}); term left on the entry-level "
      f"deal {b1:.4f} (se {s1:.2f}); change {100 * (b1 / b0 - 1):+.2f}%; as shares of the cap "
      f"{100 * b0 / (CAP_NOW / 1e6):.2f}% and {100 * b1 / (CAP_NOW / 1e6):.2f}%")
