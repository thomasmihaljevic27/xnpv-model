"""
pick_goalie_test.py -- goalies in the pick curve: with skaters, apart, or left out.

WHY (MODEL_DIRECTIVES.md directive 6; Thomas 2026-10-09: test all three, first
guess skaters only). The adopted curve is surplus = b x Bacon's star chance for
the slot (through zero, draft-year indicators), fitted on skaters. Bacon's star
is a SKATER definition (career WAR/82 of 1.8+ F, 1.23+ D); his slot baseline is
the same number for every position.

GOALIE PICKS PRICED (233 in 2007-2017; every selection), as skaters are, except:
  * WAR from SOURCE_DIR/Goalies_WAR.csv (rows split by team summed), on the
    linkage's `war_names`, seasons from the draft year on; short seasons scaled
    to 82 games as for skaters;
  * value = max(alpha_G + beta_G x WAR, league minimum share), the goalie line
    contract_npv uses (recovered from the goalie spine by
    contract_npv._recover_goalie_constants: about 0.01398 + 0.01097 per win; no
    term in the goalie line);
  * the window from draft_window_count.csv already uses the goalie Accrued
    Season (30 games); the entry-level count and the scaling of seasons under 10
    games are the skaters' rules (the CBA's 10-game slide is not position-specific).

THREE WAYS TO VALUE A PICK, AND HOW THEY ARE COMPARED
  skater scale   b fitted on skater picks only (the adopted curve), used for all
  pooled scale   b fitted on skater and goalie picks together, used for all
  apart          skater picks on the skater scale, goalie picks on a goalie scale
  Held-out miss (leave one draft class out) on the SAME targets: goalie picks'
  surplus under each way; skater picks' surplus under skater vs pooled; all picks.
  REPORT ONLY: no bar was declared for this test before it ran. Note for the
  reading: at a trade, the pick's eventual position is not known.

Run from the repo root:  python 25_TESTS/pick_goalie_test.py
"""

import os
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

SCRIPT_VERSION = "pick_goalie_test.py v1.0 (2026-10-09)"
load_dotenv()
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
import skater_forward_projection as sfp          # noqa: E402
import rfa_terminal_value as rtv                 # noqa: E402
import contract_npv as cnpv                      # noqa: E402  goalie line (recovered on import)

SOURCE_DIR, OUTPUT_DIR = Path(os.environ["SOURCE_DIR"]), Path(os.environ["OUTPUT_DIR"])
print(SCRIPT_VERSION)
F = {"linkage": OUTPUT_DIR / "draft_pick_linkage.csv", "windows": OUTPUT_DIR / "draft_window_count.csv",
     "GWAR": SOURCE_DIR / "Goalies_WAR.csv", "skaters": OUTPUT_DIR / "pick_first_look_players.csv",
     "fl_log": OUTPUT_DIR / "pick_first_look_log.txt", "bacon": SOURCE_DIR / "draft_slot_baseline.csv"}
for k, p in F.items():
    print(f"  input {k}: {p.resolve()}  (modified {pd.Timestamp(p.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M})")
assert F["fl_log"].read_text(encoding="utf-8").startswith("pick_regression_first_look.py v1.1")
AG, BG = cnpv.ALPHA_G, cnpv.BETA_G
print(f"  goalie line: alpha {AG:.6f}, beta {BG:.6f} per win (cap share)")

CAP = {2007: 50.3e6, 2008: 56.7e6, 2009: 56.8e6, 2010: 59.4e6, 2011: 64.3e6, 2012: 60.0e6, 2013: 64.3e6,
       2014: 69.0e6, **{y: sfp.CAP_CEILING[y] for y in range(2015, 2026)}}
LMIN = {2007: 475_000, 2008: 475_000, 2009: 500_000, 2010: 500_000, 2011: 525_000, 2012: 525_000,
        2013: 550_000, 2014: 550_000, **{y: sfp.league_min_path(y) for y in range(2015, 2026)}}
ELC_MAX = {**{y: 875_000 for y in (2007, 2008)}, **{y: 900_000 for y in (2009, 2010)},
           **{y: 925_000 for y in range(2011, 2018)}}
SHORT = {2012: 82 / 48, 2019: 82 / 70, 2020: 82 / 56}
CAP_NOW, CAMEO_GP, LAST_START = sfp.CAP_CEILING[2025], 10, 2025


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z ]", "", s.lower()).strip()


link = pd.read_csv(F["linkage"], parse_dates=["birthDate"])
win = pd.read_csv(F["windows"])
g = link[link["draftYear"].between(2007, 2017) & link["is_goalie"].astype(bool)].merge(
    win[["draftYear", "overall", "end_g3"]], left_on=["draftYear", "overallPickNumber"],
    right_on=["draftYear", "overall"], validate="one_to_one")
g = g[g["end_g3"].notna()]
gw = pd.read_csv(F["GWAR"], usecols=["Goalie", "Season", "GP", "WAR"])
gw["name_n"] = gw["Goalie"].map(norm)
gw["start"] = gw["Season"].map(lambda s: 2000 + int(str(s)[:2]))
gw = gw.groupby(["name_n", "start"])[["GP", "WAR"]].sum()


def goalie_surplus(row):
    if pd.isna(row["war_names"]):
        return 0.0
    parts = [gw.loc[n] for n in {norm(x) for x in str(row["war_names"]).split("|")} if n in gw.index.get_level_values(0)]
    if not parts:
        return 0.0
    s = pd.concat(parts).groupby(level=0).sum()
    s = s[s.index >= row["draftYear"]]
    last = min(int(row["end_g3"]) - 1, LAST_START)
    played = s[(s["GP"] > 0) & (s.index <= last)]
    if played.empty:
        return 0.0
    first = int(played.index.min())
    age = int((pd.Timestamp(first, 9, 15) - row["birthDate"]).days / 365.25) if pd.notna(row["birthDate"]) else 19
    n_elc = 3 if age <= 21 else 2 if age <= 23 else 1
    elc_done, prior, tot = 0, None, 0.0
    for y in range(int(row["draftYear"]), last + 1):
        gp = float(s.loc[y, "GP"]) if y in s.index else 0.0
        wins = float(s.loc[y, "WAR"]) * SHORT.get(y, 1.0) if y in s.index else 0.0
        in_elc = elc_done < n_elc and gp > 0
        if not in_elc and elc_done >= n_elc:
            prior = rtv.qualifying_offer(prior or ELC_MAX[row["draftYear"]], prior or ELC_MAX[row["draftYear"]], y, False)
        if gp == 0:
            continue
        sc = gp / 82 if gp < CAMEO_GP else 1.0
        value = max(AG + BG * wins, LMIN[y] / CAP[y]) * sc
        cost = (ELC_MAX[row["draftYear"]] if in_elc else prior) / CAP[y] * sc
        tot += value - cost
        if in_elc and gp >= CAMEO_GP:
            elc_done += 1
    return tot


g["surplus"] = g.apply(goalie_surplus, axis=1) * CAP_NOW
sk = pd.read_csv(F["skaters"])
bacon = pd.read_csv(F["bacon"]).set_index("draft_pick")["p_star"]
d = pd.concat([sk[["draftYear", "pick", "surplus"]].assign(goalie=False),
               g.rename(columns={"overallPickNumber": "pick"})[["draftYear", "pick", "surplus"]].assign(goalie=True)])
d["y"], d["p_star"] = d["surplus"] / 1e6, d["pick"].map(bacon)
print(f"\ngoalie picks {int(d['goalie'].sum())}; played an NHL game: "
      f"{int((g['surplus'] != 0).sum())}; mean surplus ${d.loc[d['goalie'], 'y'].mean():.2f}M "
      f"(skaters ${d.loc[~d['goalie'], 'y'].mean():.2f}M)")
top = g.nlargest(6, "surplus")[["draftYear", "overallPickNumber", "playerName", "surplus"]]
print(top.assign(surplus=top["surplus"] / 1e6).round(2).to_string(index=False))
CL = sorted(d["draftYear"].unique())


def fit_b(frame):
    yrs = frame["draftYear"].values
    X = np.zeros((len(frame), len(CL) - 1))
    for j, c in enumerate(CL[:-1]):
        X[:, j] = (yrs == c)
    X[yrs == CL[-1], :] = -1.0
    b, *_ = np.linalg.lstsq(np.column_stack([frame["p_star"].values, X]), frame["y"].values, rcond=None)
    return b[0]


print("\nSCALES on all classes ($M per 100% star chance): "
      f"skaters {fit_b(d[~d['goalie']]):.2f}, pooled {fit_b(d):.2f}, goalies {fit_b(d[d['goalie']]):.2f}")
pred = {k: np.empty(len(d)) for k in ("skater scale", "pooled scale", "apart")}
for c in CL:
    tr, te = d[d["draftYear"] != c], (d["draftYear"] == c).values
    bs, bp, bg = fit_b(tr[~tr["goalie"]]), fit_b(tr), fit_b(tr[tr["goalie"]])
    ps = d["p_star"].values[te]
    pred["skater scale"][te] = bs * ps
    pred["pooled scale"][te] = bp * ps
    pred["apart"][te] = np.where(d["goalie"].values[te], bg, bs) * ps
rm = lambda k, m: np.sqrt(np.mean((d["y"].values[m] - pred[k][m]) ** 2))
gm, sm_ = d["goalie"].values, ~d["goalie"].values
print("\nHELD-OUT MISS ($M a pick, leave one class out)")
print(pd.DataFrame({k: {"goalie picks": rm(k, gm), "skater picks": rm(k, sm_), "all picks": rm(k, np.ones(len(d), bool))}
                    for k in pred}).round(4).to_string())
print(f"  (a constant zero for goalie picks misses by {np.sqrt(np.mean(d['y'].values[gm] ** 2)):.4f})")
