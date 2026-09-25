"""
=============================================================================
 valuation_walkthrough.py   v1.0                 Viewer tool (2026-09-25)
=============================================================================
 WHAT THIS PRODUCES (plain English)
 ----------------------------------
 A worked example of the production aging curve for three real forwards,
 each valued on the day he was traded:

   Ryan O'Reilly     Buffalo -> St. Louis   July 1, 2018        page 2018-19
   Nazem Kadri       Toronto -> Colorado    July 1, 2019        page 2019-20
   Max Pacioretty    Montreal -> Vegas      September 10, 2018  page 2018-19

 For each one it shows, with the real numbers:
   1. his season-by-season WAR (Patrick Bacon's export, 10_SOURCE/WAR.csv),
   2. his starting level (the 60/40 trailing average the contract is priced on),
   3. his comparison profile: the eight measures, raw, standardised, weighted,
   4. the yardstick (one shared number) and how it turns a distance into a weight,
   5. every eligible comparable, how far each sits from him, and its weight,
   6. how those weights set the "players like him" pull and each yearly aging
      step, and how the resulting curve becomes projected WAR by season.
 Dollars, survival and surplus are deliberately out of scope.

 Outputs (all gitignored, 30_OUTPUT/):
   aging_walkthrough.xlsx      the workbook, live Excel formulas throughout
   aging_walkthrough.json      the key numbers, for the explainer document
   aging_walkthrough_log.txt   the run log, including every guard result

 NOTHING IN PRODUCTION CHANGES
 -----------------------------
 This script imports aging_curve.py and skater_forward_projection.py and only
 READS them. It recomputes each step by hand, in the open, and then refuses to
 write anything unless its hand arithmetic agrees with production:
   (a) the yardstick, recomputed with the same seed, equals AgingModel.h,
   (b) every comparable's weight equals AgingModel._weights() to 1e-12,
   (c) the curve path equals AgingModel.project() to 1e-12,
   (d) the per-season multipliers equal SkaterProjector.ratio_path() to 1e-12,
   (e) the starting level equals SkaterProjector.anchor() (full mode only),
   (f) the saved workbook, evaluated with Excel's operator rules (LibreOffice
       via XLSX_RECALC, else the pure-Python `formulas` package), gives the
       same weights, pulled level, steps and projected WAR as Python to 1e-9.
 Guard (e) and the age / horizon cross-checks need the contract spine, which
 only exists on the machine that holds the PuckPedia export. Without it the
 script runs in LIGHT mode and says so in the log: the curve guards still run,
 the starting level is checked against an independent re-derivation only.

 FIGURES THAT ARE INPUTS, NOT MODEL OUTPUTS (flagged here, checked where possible)
 ---------------------------------------------------------------------------------
 * Trade dates and the number of contract seasons remaining are public facts
   typed in below (PLAYERS). In full mode the horizon is checked against the
   production contract chain as of the trade date; in light mode it is not.
 * Pacioretty's four-year Vegas extension was signed on the day of the trade,
   so valued AS OF the trade date it is part of what Vegas acquired (the v1.3
   extension rule in skater_forward_projection.py). Valued on July 1, 2018 it
   would not be, and his horizon would be one season.
 * The valuation age is his age in the last completed season plus one. Both
   come from WAR_with_age.csv, which uses the same February 1 rule as the
   projection's age_at(); full mode asserts they agree.

 USAGE (from the repo root):   python 20_CODE/valuation_walkthrough.py
=============================================================================
"""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

SCRIPT_VERSION = "valuation_walkthrough.py v1.0 (2026-09-25)"

load_dotenv()
REPO = Path(__file__).resolve().parent.parent
# The production modules read these at import. Fall back to the repo layout so
# the walkthrough runs anywhere the standard tree exists; an .env still wins.
os.environ.setdefault("SOURCE_DIR", str(REPO / "10_SOURCE"))
os.environ.setdefault("OUTPUT_DIR", str(REPO / "30_OUTPUT"))
sys.path.insert(0, str(REPO / "20_CODE"))

import aging_curve as ac                                     # noqa: E402
from aging_curve import AgingModel, career_key               # noqa: E402
import skater_forward_projection as sfp                      # noqa: E402

SOURCE_DIR = Path(os.environ["SOURCE_DIR"])
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
F_WAR = SOURCE_DIR / "WAR.csv"
F_WAR_AGE = OUTPUT_DIR / "WAR_with_age.csv"
OUT_XLSX = OUTPUT_DIR / "aging_walkthrough.xlsx"
OUT_JSON = OUTPUT_DIR / "aging_walkthrough.json"
OUT_LOG = OUTPUT_DIR / "aging_walkthrough_log.txt"

# Season-length adjustment. Same dict the value engine uses (D20); importing
# skater_value_engine needs the PuckPedia path set, so fall back to the copy
# skater_forward_projection itself falls back to. Guarded below.
try:
    from skater_value_engine import PRORATION
except Exception:                                            # noqa: BLE001
    PRORATION = {2019: 82 / 70, 2020: 82 / 56}

# ---------------------------------------------------------------------------
# THE THREE EXAMPLES. t0 = the valuation page (season start year). A trade on
# or after July 1 of year Y uses page Y (player_dashboard.py date rule).
# horizon = contract seasons remaining AFTER the valuation season, counting
# extensions signed on or before the trade date.
# ---------------------------------------------------------------------------
PLAYERS = [
    dict(short="OReilly", name="Ryan O'Reilly", trade="Buffalo to St. Louis",
         trade_date="2018-07-01", t0=2018, horizon=4,
         contract_note="7 years signed 2015, runs through 2022-23"),
    dict(short="Kadri", name="Nazem Kadri", trade="Toronto to Colorado",
         trade_date="2019-07-01", t0=2019, horizon=2,
         contract_note="6 years signed 2016, runs through 2021-22"),
    dict(short="Pacioretty", name="Max Pacioretty", trade="Montreal to Vegas",
         trade_date="2018-09-10", t0=2018, horizon=4,
         contract_note=("final year of his Montreal deal in 2018-19, plus a "
                        "4-year Vegas extension signed the day of the trade "
                        "(2019-20 through 2022-23)")),
]

STYLE_LABELS = {
    "sh_EVO": ("Even-strength offence share", "his even-strength offence WAR as a share of his total style WAR"),
    "sh_EVD": ("Even-strength defence share", "his even-strength defence WAR as a share of his total style WAR"),
    "sh_PP": ("Power-play share", "his power-play WAR as a share of his total style WAR"),
    "sh_PK": ("Penalty-kill share", "his penalty-kill WAR as a share of his total style WAR"),
    "sh_Shoot": ("Shooting share", "his shooting WAR as a share of his total style WAR"),
    "toi_pg": ("Ice time per game (min)", "total minutes over the window divided by total games"),
    "lvl": ("Production level (WAR per 82)", "simple average of the two seasons' WAR per 82 games"),
    "slope": ("Production trend (WAR per 82, per year)", "later season's WAR per 82 minus the earlier season's"),
}
TOL = 1e-12

LOG = []


def log(msg=""):
    print(msg)
    LOG.append(str(msg))


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def season_label(start_year):
    """2018 -> '2018-19'."""
    return f"{start_year}-{str(start_year + 1)[-2:]}"


# ---------------------------------------------------------------------------
# SOURCE ROWS
# ---------------------------------------------------------------------------
def war_rows(name):
    """Every WAR.csv season for one player, team halves summed (review item
    1.5 rule: add the halves, refuse if the total exceeds 82 games)."""
    war = pd.read_csv(F_WAR)
    w = war[war["Player"] == name].copy()
    assert len(w), f"{name} not found in WAR.csv"
    w["syr"] = w["Season"].str.split("-").str[0].astype(int) + 2000
    num = ["GP", "TOI", "EVO WAR", "EVD WAR", "PP WAR", "PK WAR", "Pens WAR",
           "Shoot WAR", "WAR"]
    g = (w.groupby("syr", as_index=False)
          .agg(**{c: (c, "sum") for c in num}, Team=("Team", "/".join),
               Position=("Position", "last")))
    assert (g["GP"] <= 82).all(), f"{name}: a combined season exceeds 82 games"
    return g.sort_values("syr").reset_index(drop=True)


def curve_season_labels():
    """(career key, age) -> season start year, for the curve's own qualifying
    seasons. Rebuilt with the same steps as AgingModel.__init__ (clean the
    name, drop merged names, sum team halves, keep GP >= 20)."""
    df = pd.read_csv(F_WAR_AGE)
    df["career"] = df["Player"].map(career_key)
    df = df[~df["career"].isin(ac.MERGED_WAR_NAMES)]
    g = (df.groupby(["career", "Season"], as_index=False)
           .agg(GP=("GP", "sum"), age=("age", "first")))
    g = g[g["age"].notna() & (g["GP"] >= ac.MIN_GP)]
    g["syr"] = g["Season"].str.split("-").str[0].astype(int) + 2000
    out = {}
    for r in g.itertuples():
        out[(r.career, int(r.age))] = int(r.syr)
    # every season's age, whatever the games played (display only)
    allg = df[df["age"].notna()].copy()
    allg["syr"] = allg["Season"].str.split("-").str[0].astype(int) + 2000
    ages_all = {(r.career, int(r.syr)): int(r.age) for r in allg.itertuples()}
    return out, ages_all


# ---------------------------------------------------------------------------
# STEP 4: THE YARDSTICK, recomputed exactly as AgingModel._build_bank does it
# ---------------------------------------------------------------------------
def yardstick(m):
    """Up to 1,200 profiles are drawn per position (seed 0, all ages mixed),
    the distance between every pair WITHIN a position is measured, and the
    forward and defence distances are pooled. The median of that pool is the
    yardstick. Returns the recomputed value plus descriptive statistics."""
    rng = np.random.default_rng(0)
    pools, per_pos = [], {}
    for pp in np.unique(m.pos):                       # sorted: 'D' then 'F'
        Xi = m.Zw[m.pos == pp]
        if len(Xi) < 3:
            continue
        idx = rng.choice(len(Xi), size=min(1200, len(Xi)), replace=False)
        Xi = Xi[idx]
        sq = (Xi ** 2).sum(1)
        d2 = np.clip(sq[:, None] + sq[None, :] - 2 * Xi @ Xi.T, 0, None)
        d = np.sqrt(d2[np.triu_indices(len(Xi), 1)])
        pools.append(d)
        per_pos[pp] = dict(profiles_in_pool=int((m.pos == pp).sum()),
                           profiles_sampled=int(len(Xi)), pairs=int(len(d)),
                           median=float(np.median(d)))
    pooled = np.concatenate(pools)
    h = float(np.median(pooled))
    pct = {str(q): float(np.percentile(pooled, q)) for q in (10, 25, 50, 75, 90)}
    return h, pooled, per_pos, pct


def same_age_median(m, pos, age):
    """What the yardstick WOULD be if it were built only from players of this
    position and age (all pairs, no sampling). Reported for comparison only;
    production does not do this."""
    Xi = m.Zw[(m.pos == pos) & (m.agek == age)]
    sq = (Xi ** 2).sum(1)
    d2 = np.clip(sq[:, None] + sq[None, :] - 2 * Xi @ Xi.T, 0, None)
    return float(np.median(np.sqrt(d2[np.triu_indices(len(Xi), 1)]))), len(Xi)


# ---------------------------------------------------------------------------
# ONE PLAYER, BY HAND
# ---------------------------------------------------------------------------
def walk(m, sp, full, P, labels):
    t0, horizon = P["t0"], P["horizon"]
    key = career_key(P["name"])
    assert key in m.players, f"{P['name']} has no career in the aging model"
    p = m.players[key]
    pos = p["pos"]
    ss = p["seasons"]
    rows = war_rows(P["name"])
    nk = sfp.norm_name(P["name"]) + "|" + rows["Position"].iloc[-1]

    # ---- STEP 2: starting level (Layer 1 rule, D20 season-length first) ----
    rows["factor"] = rows["syr"].map(PRORATION).fillna(1.0)
    rows["war_adj"] = rows["WAR"] * rows["factor"]
    rows["w82"] = rows["WAR"] / rows["GP"] * 82.0
    lut = rows.set_index("syr")
    def q(y):   # qualifying season total, or None
        if y in lut.index and lut.loc[y, "GP"] >= sfp.MIN_GP:
            return float(lut.loc[y, "war_adj"])
        return None
    w1, w2 = q(t0 - 1), q(t0 - 2)
    if w1 is not None and w2 is not None:
        anchor, src = sfp.W_T1 * w1 + sfp.W_T2 * w2, "both"
    elif w1 is not None:
        anchor, src = w1, "t1_only"
    elif w2 is not None:
        anchor, src = w2, "t2_only"
    else:
        raise ValueError(f"{P['name']}: no qualifying trailing season")
    if full:
        a_prod, s_prod = sp.anchor(nk, t0)
        assert abs(a_prod - anchor) < TOL and s_prod == src, \
            f"{P['name']}: starting level {anchor} != production {a_prod}"
        log(f"  guard (e) starting level matches production: {anchor:.6f} ({src})")
    else:
        log(f"  guard (e) SKIPPED (light mode): starting level {anchor:.6f} ({src}) "
            "from the independent re-derivation only")

    # ---- valuation age: age in the last completed season, plus one ---------
    ages_by_syr = {}
    for (ck, a), y in labels.items():
        if ck == key:
            ages_by_syr[y] = a
    assert (t0 - 1) in ages_by_syr, f"{P['name']}: no qualifying season in {t0 - 1}"
    age = ages_by_syr[t0 - 1] + 1

    # ---- STEP 3: where the curve is based (D21: age-1, fallback age-2) ------
    # Replicates ratio_path()'s lag loop exactly, including its horizon guard.
    max_age = m.AMIN + m.nages - 1
    base_age = lag = safe_h = None
    for lg in (1, 2):
        b = age - lg
        sh = min(horizon + lg, max(0, max_age - b - 1))
        if sh < lg + 1:
            continue
        if not any(s["age"] == b for s in ss):
            continue
        base_age, lag, safe_h = b, lg, sh
        break
    assert base_age is not None, f"{P['name']}: curve unavailable (flat_no_curve)"
    idx = next(i for i, s in enumerate(ss) if s["age"] == base_age)
    adjacent = p["adjacent"].get(base_age, False)
    lo = idx if not adjacent else max(0, idx - (ac.WIN - 1))
    window = ss[lo: idx + 1]
    win_years = [labels[(key, s["age"])] for s in window]

    # the curve's season rows must be the same numbers as WAR.csv's
    for s, y in zip(window, win_years):
        r = lut.loc[y]
        assert r["GP"] == s["gp"] and abs(r["TOI"] - s["toi"]) < 1e-9 and \
            abs(r["WAR"] / r["GP"] * 82 - s["w82"]) < 1e-9, \
            f"{P['name']} {y}: WAR_with_age and WAR.csv disagree"

    # ---- the target profile, measure by measure ----------------------------
    sm_level = p["sm"][base_age]
    raw = ac._profile(window, sm_level)                     # production helper
    comp = np.sum([s["comp"] for s in window], axis=0)       # our own derivation
    gross = np.sum(np.abs(comp))
    mine = list(comp / gross) + [sum(s["toi"] for s in window) / sum(s["gp"] for s in window),
                                 float(np.mean([s["w82"] for s in window])) if adjacent else window[-1]["w82"],
                                 (window[-1]["w82"] - window[0]["w82"]) / (window[-1]["age"] - window[0]["age"])
                                 if len(window) > 1 else 0.0]
    assert np.allclose(raw, mine, atol=TOL, rtol=0), f"{P['name']}: profile re-derivation differs"
    mu, sd = m.stats[pos]
    fw = m.fw
    tz = (raw - mu) / sd                                     # standard scores
    tzw = tz * np.sqrt(fw)                                   # after measure weights

    # ---- STEP 5: every eligible comparable, distance and weight ------------
    cand = m.by_age[base_age]
    cand = cand[m.pos[cand] == pos]
    diff = m.Zw[cand] - tzw
    contrib = diff ** 2                                      # per-measure pieces of d^2
    d = np.sqrt(contrib.sum(1))
    w = np.exp(-(d ** 2) / (2 * m.h ** 2))
    w[m.names[cand] == key] = 0.0                            # his own career is excluded
    c_prod, w_prod = m._weights(tzw, pos, base_age, exclude=key)
    assert np.array_equal(c_prod, cand) and np.max(np.abs(w_prod - w)) < TOL, \
        f"{P['name']}: hand weights differ from AgingModel._weights()"
    log(f"  guard (b) {len(cand)} comparable weights match production "
        f"(max abs diff {np.max(np.abs(w_prod - w)):.1e})")
    keep = m.names[cand] != key
    self_rows = int((~keep).sum())

    # comparables' raw measures, rebuilt from their own seasons (exact)
    comps = []
    for j, r in enumerate(cand):
        if not keep[j]:
            continue
        nm, a_r = m.names[r], int(m.agek[r])
        cp = m.players[nm]
        cs = cp["seasons"]
        i = next(k for k, s in enumerate(cs) if s["age"] == a_r)
        X = ac._profile(cs[i - 1: i + 1], cp["sm"][a_r])
        assert np.allclose((X - mu) / sd * np.sqrt(fw), m.Zw[r], atol=1e-10, rtol=0)
        y2 = labels[(nm, a_r)]
        y1 = labels[(nm, cs[i - 1]["age"])]
        # yearly changes this comparable contributes to each step of the walk
        steps = {}
        for k in range(1, safe_h + 1):
            a = base_age + k - 1
            dv = m.Dser[r, a - m.AMIN]
            after = None
            if not np.isnan(dv):
                after = int(labels[(nm, a + 1)] >= t0)       # transition ends after valuation?
            steps[a] = (None if np.isnan(dv) else float(dv), after)
        comps.append(dict(row=int(r), name=nm, display=display_name(nm), age=a_r,
                          seasons=f"{season_label(y1)} & {season_label(y2)}",
                          after=int(y2 >= t0), X=X, z=(X - mu) / sd,
                          contrib=contrib[j], d=float(d[j]), w=float(w[j]),
                          lvl=float(m.Lser[r, base_age - m.AMIN]), steps=steps))
    comps.sort(key=lambda c: -c["w"])
    W = np.array([c["w"] for c in comps])

    # ---- STEP 6a: the "players like him" level and the pulled start --------
    K, LAM = ac.SHRINK_K, ac.LAMBDA
    glevel = m.glevel.get((pos, base_age), sm_level)
    L = np.array([c["lvl"] for c in comps])
    norm = (np.sum(W * L) + K * glevel) / (W.sum() + K)
    start = LAM * sm_level + (1 - LAM) * norm

    # ---- STEP 6b: the yearly aging steps -----------------------------------
    levels = [start]
    step_rows = []
    for k in range(1, safe_h + 1):
        a = base_age + k - 1
        D = np.array([np.nan if c["steps"][a][0] is None else c["steps"][a][0] for c in comps])
        has = ~np.isnan(D)
        gd = m.gdelta.get((pos, a), 0.0)
        wt = float((W * has).sum())
        num = float(np.nansum(W * np.where(has, D, 0.0)))
        step = (num + K * gd) / (wt + K)
        aft = np.array([c["steps"][a][1] or 0 for c in comps])
        step_rows.append(dict(from_age=a, to_age=a + 1, n=int(has.sum()), weight=wt,
                              comp_avg=num / wt if wt > 0 else None, league=gd, step=step,
                              after_share=float((W * has * aft).sum() / wt) if wt > 0 else None,
                              level_after=levels[-1] + step))
        levels.append(levels[-1] + step)
    tr = m.project(key, current_age=base_age, horizon=safe_h)
    assert np.max(np.abs(tr["projected_war_per_82"].to_numpy() - np.array(levels))) < TOL, \
        f"{P['name']}: hand curve differs from AgingModel.project()"
    log(f"  guard (c) curve path matches AgingModel.project() at {len(levels)} ages")

    # ---- STEP 7: curve -> per-season multipliers -> projected WAR ---------
    lv = levels[lag:]
    base = lv[0]
    flat = base <= sfp.CURVE_BASE_FLOOR
    ratios_raw = [x / base for x in lv]
    ratios = [min(max(r_, sfp.RATIO_FLOOR), sfp.RATIO_CAP) for r_ in ratios_raw]
    while len(ratios) < horizon + 1:
        ratios.append(ratios[-1])
    if flat:
        ratios = [1.0] * (horizon + 1)
    prod_ratios, path = sp.ratio_path(nk, age, horizon)
    # Tolerance, not bit equality: the hand-built curve adds the same terms in
    # a different order from AgingModel.project(), so the last digit can differ.
    assert len(prod_ratios) == len(ratios) and \
        np.max(np.abs(np.array(prod_ratios) - np.array(ratios))) < TOL, \
        f"{P['name']}: multipliers differ from ratio_path()"
    log(f"  guard (d) multipliers match SkaterProjector.ratio_path() to 1e-12 (path={path})")
    proj = [anchor * sfp.SkaterProjector.multiplier(anchor, ratios[k], k)
            for k in range(horizon + 1)]
    seasons_out = []
    for k in range(horizon + 1):
        y = t0 + k
        act = lut.loc[y] if y in lut.index else None
        seasons_out.append(dict(
            season=season_label(y), k=k, age=age + k, curve_level=lv[k] if k < len(lv) else lv[-1],
            multiplier_raw=ratios_raw[k] if k < len(ratios_raw) else ratios_raw[-1],
            multiplier=ratios[k], projected_war=proj[k],
            actual_gp=None if act is None else int(act["GP"]),
            actual_war=None if act is None else float(act["WAR"]),
            actual_war_adj=None if act is None else float(act["war_adj"])))
    if full:
        pc = sp.project_contract(sp_player_id(sp, nk, t0), t0, as_of=P["trade_date"])
        assert len(pc) == horizon + 1, \
            f"{P['name']}: horizon {horizon} != production contract chain {len(pc) - 1}"
        assert int(pc["age_at_valuation"].iloc[0]) == age
        assert np.allclose(pc["projected_war"].to_numpy(), proj, atol=TOL, rtol=0)
        log("  full-mode checks: horizon, valuation age and projected WAR match project_contract()")

    return dict(
        P=P, key=key, pos=pos, nk=nk, rows=rows, anchor=anchor, anchor_src=src,
        w1=w1, w2=w2, age=age, base_age=base_age, lag=lag, safe_h=safe_h,
        window=window, win_years=win_years, adjacent=adjacent, raw=raw, tz=tz,
        tzw=tzw, comps=comps, self_rows=self_rows, glevel=glevel, norm=norm,
        sm_level=sm_level, start=start, step_rows=step_rows, levels=levels,
        flat=flat, seasons=seasons_out, path=path,
        sum_w=float(W.sum()), eff_n=float(W.sum() ** 2 / (W ** 2).sum()),
        top5_share=float(W[:5].sum() / W.sum()),
        after_share=float(sum(c["w"] for c in comps if c["after"]) / W.sum()),
        n_after=int(sum(c["after"] for c in comps)))


def display_name(career):
    """Title-case a career key for display ('ryan o reilly' -> 'Ryan O Reilly').
    Display only; every join in this file uses the key itself."""
    return " ".join(t.capitalize() for t in career.split())


def sp_player_id(sp, nk, t0):
    r = sp.spine[(sp.spine["nk"] == nk) & (sp.spine["season_start"] == t0)]
    assert len(r["player_id"].unique()) == 1, f"{nk}: no unique spine player at {t0}"
    return r["player_id"].iloc[0]


def light_projector(m):
    """A SkaterProjector carrying only what ratio_path() reads (the fitted
    curve and the name map), built exactly as SkaterProjector.__init__ builds
    them. Used when the contract spine is not on this machine."""
    sp = object.__new__(sfp.SkaterProjector)
    sp.curve = m
    war = pd.read_csv(F_WAR)
    war["nk"] = war["Player"].map(sfp.norm_name) + "|" + war["Position"]
    war = war[~war["Player"].map(sfp.norm_name).isin(sfp.MERGED_WAR_NAMES)]
    sp.raw_name = war.drop_duplicates("nk").set_index("nk")["Player"].to_dict()
    return sp


# ===========================================================================
# THE WORKBOOK
# ===========================================================================
from openpyxl import Workbook                                       # noqa: E402
from openpyxl.comments import Comment                               # noqa: E402
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side  # noqa: E402
from openpyxl.utils import get_column_letter as CL                  # noqa: E402
from openpyxl.workbook.defined_name import DefinedName              # noqa: E402

F_BASE = "Arial"
BLUE = Font(name=F_BASE, color="0000FF")          # typed-in data from source files
BLACK = Font(name=F_BASE, color="000000")         # formulas
GREEN = Font(name=F_BASE, color="008000")         # links to another sheet
GREY = Font(name=F_BASE, color="808080", italic=True)
BOLD = Font(name=F_BASE, bold=True)
TITLE = Font(name=F_BASE, bold=True, size=14)
HEAD = Font(name=F_BASE, bold=True, color="FFFFFF")
HEAD_FILL = PatternFill("solid", fgColor="1F3864")
KEY_FILL = PatternFill("solid", fgColor="FFF2CC")
HIND_FILL = PatternFill("solid", fgColor="EDEDED")
WRAP = Alignment(wrap_text=True, vertical="top")
THIN = Border(bottom=Side(style="thin", color="999999"))
N3, N4, N2 = "0.000", "0.0000", "0.00"


def ref(ws, cell, absolute=True):
    """Cross-sheet reference with the sheet name always quoted."""
    c = cell
    if absolute:
        col = "".join(ch for ch in cell if ch.isalpha())
        row = "".join(ch for ch in cell if ch.isdigit())
        c = f"${col}${row}"
    return f"'{ws.title}'!{c}"


def put(ws, cell, value, font=BLACK, fmt=None, fill=None, bold=False):
    c = ws[cell]
    c.value = value
    c.font = Font(name=F_BASE, bold=bold, color=font.color, italic=font.italic)
    if fmt:
        c.number_format = fmt
    if fill:
        c.fill = fill
    return c


def header(ws, row, col, labels, widths=None):
    for i, lab in enumerate(labels):
        c = ws.cell(row=row, column=col + i, value=lab)
        c.font, c.fill, c.alignment = HEAD, HEAD_FILL, Alignment(wrap_text=True, vertical="center")
        if widths:
            ws.column_dimensions[CL(col + i)].width = widths[i]
    ws.row_dimensions[row].height = 45


def note(ws, cell, text, width_cols=10):
    c = ws[cell]
    c.value = text
    c.font = Font(name=F_BASE, italic=True, color="404040")
    c.alignment = WRAP
    r = c.row
    ws.merge_cells(start_row=r, start_column=c.column, end_row=r, end_column=c.column + width_cols - 1)
    ws.row_dimensions[r].height = max(15, 15 * (1 + len(text) // 120))


def name(wb, label, ws, cell):
    col = "".join(ch for ch in cell if ch.isalpha())
    row = "".join(ch for ch in cell if ch.isdigit())
    wb.defined_names[label] = DefinedName(label, attr_text=f"'{ws.title}'!${col}${row}")


def build_workbook(m, h_info, results):
    h, _, per_pos, pct = h_info
    wb = Workbook()
    readme = wb.active
    readme.title = "Read me"

    # ---------------- Settings ----------------
    st = wb.create_sheet("Settings")
    st.column_dimensions["A"].width = 44
    st.column_dimensions["B"].width = 14
    st.column_dimensions["C"].width = 100
    put(st, "A1", "Model settings used in every calculation", TITLE)
    note(st, "A2", "Blue numbers are copied from the production code (20_CODE/aging_curve.py and "
         "skater_forward_projection.py) or computed by it. Every formula elsewhere points at these cells, "
         "so changing one here flows through the whole workbook.", 3)
    header(st, 4, 1, ["Setting", "Value", "Where it comes from and what it does"])
    settings = [
        ("MinGP_base", "Minimum games for a season to count toward the starting level", sfp.MIN_GP, "0",
         "skater_forward_projection.py MIN_GP. A season with fewer games is ignored for the starting level."),
        ("MinGP_curve", "Minimum games for a season to count in the aging model", ac.MIN_GP, "0",
         "aging_curve.py MIN_GP. Applies to the player's own profile seasons and to every comparable."),
        ("W_recent", "Starting level: weight on last season", sfp.W_T1, N2,
         "skater_forward_projection.py W_T1."),
        ("W_older", "Starting level: weight on the season before", sfp.W_T2, N2,
         "skater_forward_projection.py W_T2."),
        ("Yardstick", "Yardstick (median profile distance)", h, N4,
         "AgingModel.h, recomputed on the Yardstick sheet. One number for every player, both positions, all ages."),
        ("K_league", "Weight given to the league average (in comparable-weight units)", ac.SHRINK_K, "0.0",
         "aging_curve.py SHRINK_K. Every 'players like him' average is blended with the league average for his "
         "position and age as if the league average were one more comparable carrying this much weight."),
        ("Lambda", "Share of the starting curve level kept from his own production", ac.LAMBDA, N2,
         "aging_curve.py LAMBDA. The rest (1 - Lambda) comes from the 'players like him' level."),
        ("RatioFloor", "Lowest multiplier allowed", sfp.RATIO_FLOOR, N2,
         "skater_forward_projection.py RATIO_FLOOR: a projection can fall to replacement level, not below."),
        ("RatioCap", "Highest multiplier allowed", sfp.RATIO_CAP, N2, "skater_forward_projection.py RATIO_CAP."),
        ("BaseFloor", "Curve level at or below which multipliers are not used", sfp.CURVE_BASE_FLOOR, N2,
         "skater_forward_projection.py CURVE_BASE_FLOOR: dividing by a curve level this close to zero is "
         "unstable, so the projection holds flat instead."),
    ]
    r = 5
    for nm_, lab, val, fmt, src in settings:
        put(st, f"A{r}", lab)
        put(st, f"B{r}", val, BLUE, fmt, KEY_FILL)
        put(st, f"C{r}", src).alignment = WRAP
        name(wb, nm_, st, f"B{r}")
        r += 1

    r += 1
    put(st, f"A{r}", "The eight profile measures (forwards)", BOLD)
    r += 1
    header(st, r, 1, ["Measure", "Weight", "How it is built / plain meaning"])
    st.cell(row=r, column=4, value="Forward average").font = HEAD
    st.cell(row=r, column=4).fill = HEAD_FILL
    st.cell(row=r, column=5, value="Forward standard deviation").font = HEAD
    st.cell(row=r, column=5).fill = HEAD_FILL
    st.column_dimensions["D"].width = 16
    st.column_dimensions["E"].width = 16
    meas_row0 = r + 1
    mu, sd = m.stats["F"]
    for j, f in enumerate(ac.FEATS):
        rr = meas_row0 + j
        put(st, f"A{rr}", STYLE_LABELS[f][0])
        put(st, f"B{rr}", float(m.fw[j]), BLUE, N2, KEY_FILL)
        put(st, f"C{rr}", STYLE_LABELS[f][1]).alignment = WRAP
        put(st, f"D{rr}", float(mu[j]), BLUE, N4)
        put(st, f"E{rr}", float(sd[j]), BLUE, N4)
    rr = meas_row0 + len(ac.FEATS)
    put(st, f"A{rr}", "Total weight", BOLD)
    put(st, f"B{rr}", f"=SUM(B{meas_row0}:B{rr - 1})", BLACK, N2)
    note(st, f"A{rr + 1}",
         "Weights are the production values: each of the four groups (style, ice time, level, trend) carries "
         "1.0, and the five style shares split theirs, 0.2 each. As fractions of the total (4.0) that is 1/20 "
         "per style share and 1/4 for each of the other three. Scaling every weight by the same number would "
         "scale every distance AND the yardstick together, leaving every comparable's weight unchanged. "
         "The forward average and standard deviation are taken over every forward profile in the comparable "
         "pool, all ages together (AgingModel.stats). Penalty WAR is left out of the style shares "
         "(it made the shares add to a fixed total, so one of them carried no new information).", 5)
    st.row_dimensions[rr + 1].height = 90
    MEAS = dict(row0=meas_row0)

    # ---------------- Yardstick ----------------
    ys = wb.create_sheet("Yardstick")
    ys.column_dimensions["A"].width = 52
    for c_ in "BCDE":
        ys.column_dimensions[c_].width = 16
    put(ys, "A1", "The yardstick: one shared scale for 'near' and 'far'", TITLE)
    note(ys, "A2",
         "How production builds it (AgingModel._build_bank): take every profile in the comparable pool, "
         "separately for forwards and defencemen. Draw up to 1,200 profiles per position at random (seed 0). "
         "These are profiles of ALL ages mixed together, not just players of one age. Measure the distance "
         "between every pair of sampled forwards and every pair of sampled defencemen (never a forward against "
         "a defenceman). Pool the two lists of distances and take the middle value (the median). "
         "That median is the yardstick: one number used for every player at every age.", 5)
    ys.row_dimensions[2].height = 95
    header(ys, 4, 1, ["", "Forwards", "Defence", "Pooled"])
    rows_ = [("Profiles in the pool", "profiles_in_pool"), ("Profiles sampled", "profiles_sampled"),
             ("Pairs measured", "pairs"), ("Median distance within the group", "median")]
    for i, (lab, k_) in enumerate(rows_):
        put(ys, f"A{5 + i}", lab)
        put(ys, f"B{5 + i}", per_pos["F"][k_], BLUE, "#,##0" if k_ != "median" else N4)
        put(ys, f"C{5 + i}", per_pos["D"][k_], BLUE, "#,##0" if k_ != "median" else N4)
    put(ys, "D7", "=B7+C7", BLACK, "#,##0")
    put(ys, "D8", "=Yardstick", GREEN, N4, KEY_FILL)
    ys["D8"].comment = Comment("The pooled median is the yardstick. Production value: AgingModel.h.", "walkthrough")
    put(ys, "A10", "Spread of the pooled distances", BOLD)
    header(ys, 11, 1, ["Percentile", "Distance", "In yardsticks"])
    for i, (q_, v) in enumerate(pct.items()):
        put(ys, f"A{12 + i}", f"{q_}th percentile")
        put(ys, f"B{12 + i}", v, BLUE, N4)
        put(ys, f"C{12 + i}", f"=B{12 + i}/Yardstick", BLACK, N2)
    put(ys, "A18", "From distance to weight", BOLD)
    note(ys, "A19",
         "weight = EXP( -(distance^2) / (2 x yardstick^2) ). An exact match gets weight 1. A comparable exactly one "
         "yardstick away gets EXP(-0.5) = 0.607, which is where the 0.61 comes from: it is a weight, not a "
         "distance. Two yardsticks away gets EXP(-2) = 0.135. The fall-off speeds up with distance "
         "(it is the bell-curve shape), so far-away profiles count for almost nothing.", 5)
    ys.row_dimensions[19].height = 75
    header(ys, 21, 1, ["Distance, in yardsticks", "Distance", "Weight"])
    for i, k_ in enumerate([0, 0.25, 0.5, 0.75, 1, 1.25, 1.5, 2, 2.5, 3]):
        rr = 22 + i
        put(ys, f"A{rr}", k_, BLUE, N2)
        put(ys, f"B{rr}", f"=A{rr}*Yardstick", BLACK, N3)
        # EXP(-(B^2)...): in Excel a leading minus binds before ^, so -B^2 would be (+B^2)
        put(ys, f"C{rr}", f"=EXP(-(B{rr}^2)/(2*Yardstick^2))", BLACK, N3)
    r0 = 33
    put(ys, f"A{r0}", "For comparison only: a yardstick built from one age and position", BOLD)
    note(ys, f"A{r0 + 1}",
         "Production does NOT do this. These are the medians you would get using only forwards of each "
         "walkthrough player's comparison age (every pair, no sampling). Listed so the shared yardstick can "
         "be compared with an age-specific one.", 5)
    ys.row_dimensions[r0 + 1].height = 45
    header(ys, r0 + 3, 1, ["Player: forwards of age", "Profiles", "Median distance", "In shared yardsticks"])
    for i, R in enumerate(results):
        rr = r0 + 4 + i
        put(ys, f"A{rr}", f"{R['P']['name']}: forwards aged {R['base_age']}")
        put(ys, f"B{rr}", R["same_age_n"], BLUE, "#,##0")
        put(ys, f"C{rr}", R["same_age_median"], BLUE, N4)
        put(ys, f"D{rr}", f"=C{rr}/Yardstick", BLACK, N2)

    for R in results:
        build_player(wb, m, R, MEAS)
    build_readme(readme, results)
    wb.save(OUT_XLSX)


def build_player(wb, m, R, MEAS):
    P = R["P"]
    s = P["short"]
    t0 = P["t0"]

    # =========== 1 Seasons ===========
    ws = wb.create_sheet(f"{s} 1 Seasons")
    put(ws, "A1", f"{P['name']}: every season of WAR", TITLE)
    note(ws, "A2", f"Traded {P['trade']} on {P['trade_date']}. The model values him as of the {season_label(t0)} "
         f"season, so it may use seasons up to {season_label(t0 - 1)} only. Grey rows are later seasons, shown "
         "for hindsight and never used by the model. Source: Patrick Bacon's WAR export (10_SOURCE/WAR.csv); "
         "a season split between two teams is added together into one row.", 16)
    ws.row_dimensions[2].height = 45
    cols = ["Season", "Team", "Age", "Games", "Ice time (min)", "Even-strength offence WAR",
            "Even-strength defence WAR", "Power-play WAR", "Penalty-kill WAR", "Penalties WAR",
            "Shooting WAR", "Total WAR", "Season-length factor", "WAR, season-length adjusted",
            "WAR per 82 games", "Used by the model for"]
    header(ws, 4, 1, cols, [10, 11, 6, 7, 10, 12, 12, 11, 11, 11, 11, 10, 11, 12, 11, 34])
    ages = {y: a for (ck, y), a in AGES_ALL.items() if ck == R["key"]}
    row_of = {}
    rr = 5
    for _, x in R["rows"].iterrows():
        y = int(x["syr"])
        row_of[y] = rr
        after = y >= t0
        font = GREY if after else BLUE
        vals = [season_label(y), x["Team"], ages.get(y), int(x["GP"]), float(x["TOI"])] + \
               [float(x[c]) for c in ["EVO WAR", "EVD WAR", "PP WAR", "PK WAR", "Pens WAR", "Shoot WAR",
                                      "WAR", "factor"]]
        for j, v in enumerate(vals):
            c = put(ws, f"{CL(j + 1)}{rr}", v, font, N3 if j >= 4 else None,
                    HIND_FILL if after else None)
            if j == 12:
                c.number_format = N4
        put(ws, f"N{rr}", f"=L{rr}*M{rr}", BLACK, N3, HIND_FILL if after else None)
        put(ws, f"O{rr}", f"=L{rr}/D{rr}*82", BLACK, N3, HIND_FILL if after else None)
        use = []
        if y in (t0 - 1, t0 - 2):
            use.append(f"starting level (if {sfp.MIN_GP}+ games)")
        if y in R["win_years"]:
            use.append(f"comparison profile at age {ages[y]}")
        if after:
            use.append("hindsight only")
        put(ws, f"P{rr}", "; ".join(use) if use else "", GREY if after else BLACK,
            fill=HIND_FILL if after else None)
        rr += 1
    ws.freeze_panes = "B5"
    R["row_of"] = row_of

    b = rr + 1
    put(ws, f"A{b}", "Starting level: how good is he now?", BOLD)
    note(ws, f"A{b + 1}", "60% of last season's WAR plus 40% of the season before, each counted only if he played "
         "at least the minimum games. If only one season counts, it supplies the whole starting level. "
         "This is a season total (not a per-82 rate); it is the number the aging curve's multipliers are "
         "applied to on the Aging path sheet.", 16)
    ws.row_dimensions[b + 1].height = 45
    r1, r2 = row_of.get(t0 - 1), row_of.get(t0 - 2)
    lab = [("Last season", r1, "W_recent"), ("Season before", r2, "W_older")]
    header(ws, b + 3, 1, ["", "Season", "Games", "Adjusted WAR", "Counts?", "Weight"])
    for i, (lb, rw, wn) in enumerate(lab):
        q_ = b + 4 + i
        put(ws, f"A{q_}", lb)
        put(ws, f"B{q_}", f"=A{rw}", BLACK)
        put(ws, f"C{q_}", f"=D{rw}", BLACK, "0")
        put(ws, f"D{q_}", f"=N{rw}", BLACK, N3)
        put(ws, f"E{q_}", f"=C{q_}>=MinGP_base", BLACK)
        put(ws, f"F{q_}", f"={wn}", GREEN, N2)
    q1, q2 = b + 4, b + 5
    put(ws, f"A{b + 7}", "Starting level (WAR)", BOLD)
    put(ws, f"D{b + 7}", f"=IF(AND(E{q1},E{q2}),F{q1}*D{q1}+F{q2}*D{q2},IF(E{q1},D{q1},IF(E{q2},D{q2},NA())))",
        BLACK, N4, KEY_FILL, bold=True)
    R["cell_anchor"] = ref(ws, f"D{b + 7}")
    R["ws_seasons"] = ws

    # =========== 2 Profile ===========
    wp = wb.create_sheet(f"{s} 2 Profile")
    put(wp, "A1", f"{P['name']}: his comparison profile", TITLE)
    ba, ag = R["base_age"], R["age"]
    note(wp, "A2", f"He is {ag} in the valuation season ({season_label(t0)}). The comparison is made one season "
         f"earlier, at age {ba}, so it rests only on completed seasons ({season_label(t0 - 1)} and before). "
         f"His profile at age {ba} uses his two consecutive seasons at ages {ba - 1} and {ba}, each with at "
         f"least {ac.MIN_GP} games. It is then compared with every other forward's profile at age {ba}.", 9)
    wp.row_dimensions[2].height = 60
    header(wp, 4, 1, ["Profile season", "Age", "Games", "Ice time (min)", "EV offence WAR", "EV defence WAR",
                      "Power-play WAR", "Penalty-kill WAR", "Shooting WAR", "Total WAR", "WAR per 82"],
           [24, 7, 8, 12, 12, 12, 12, 12, 12, 10, 11])
    prow = []
    for i, y in enumerate(R["win_years"]):
        q_ = 5 + i
        prow.append(q_)
        sr = R["row_of"][y]
        wsn = R["ws_seasons"]
        for col_src, col_dst, fmt in [("A", "A", None), ("C", "B", None), ("D", "C", "0"), ("E", "D", N3),
                                      ("F", "E", N3), ("G", "F", N3), ("H", "G", N3), ("I", "H", N3),
                                      ("K", "I", N3), ("L", "J", N3), ("O", "K", N3)]:
            put(wp, f"{col_dst}{q_}", f"={ref(wsn, f'{col_src}{sr}')}", GREEN, fmt)
    a_, z_ = prow[0], prow[-1]
    two = len(prow) == 2
    gross = (f"(ABS(SUM(E{a_}:E{z_}))+ABS(SUM(F{a_}:F{z_}))+ABS(SUM(G{a_}:G{z_}))"
             f"+ABS(SUM(H{a_}:H{z_}))+ABS(SUM(I{a_}:I{z_})))")
    forms = [f"=SUM(E{a_}:E{z_})/{gross}", f"=SUM(F{a_}:F{z_})/{gross}", f"=SUM(G{a_}:G{z_})/{gross}",
             f"=SUM(H{a_}:H{z_})/{gross}", f"=SUM(I{a_}:I{z_})/{gross}",
             f"=SUM(D{a_}:D{z_})/SUM(C{a_}:C{z_})",
             f"=AVERAGE(K{a_}:K{z_})" if two else f"=K{a_}",
             f"=(K{z_}-K{a_})/(B{z_}-B{a_})" if two else "=0"]
    t = 9
    note(wp, f"A{t - 1}", "Style shares: each style WAR summed over the two seasons, divided by the sum of the "
         "five style WARs ignoring their signs (Penalties WAR is left out). They describe the MIX of his game, "
         "not its size. Standard score = (value - forward average) / forward standard deviation. "
         "Weighted score = standard score x square root of the measure weight.", 9)
    wp.row_dimensions[t - 1].height = 60
    header(wp, t, 1, ["Measure", "", "", "His value", "Forward average", "Forward SD", "Standard score",
                      "Measure weight", "Weighted score"])
    R["prof_rows"] = []
    for j, f in enumerate(ac.FEATS):
        q_ = t + 1 + j
        mr = MEAS["row0"] + j
        put(wp, f"A{q_}", STYLE_LABELS[f][0])
        put(wp, f"D{q_}", forms[j], BLACK, N4)
        put(wp, f"E{q_}", f"=Settings!$D${mr}", GREEN, N4)
        put(wp, f"F{q_}", f"=Settings!$E${mr}", GREEN, N4)
        put(wp, f"G{q_}", f"=(D{q_}-E{q_})/F{q_}", BLACK, N3)
        put(wp, f"H{q_}", f"=Settings!$B${mr}", GREEN, N2)
        put(wp, f"I{q_}", f"=G{q_}*SQRT(H{q_})", BLACK, N4, KEY_FILL)
        R["prof_rows"].append(q_)
    R["ws_profile"] = wp
    R["cell_lvl"] = ref(wp, f"D{t + 1 + 6}")

    # =========== 3 Comparables ===========
    wc = wb.create_sheet(f"{s} 3 Comparables")
    put(wc, "A1", f"{P['name']}: every forward profile at age {ba}, and how close each one is", TITLE)
    note(wc, "A2", f"Every forward with a qualifying two-season profile at age {ba} is eligible; there is no fixed "
         f"number of comparables. {P['name']}'s own career is excluded ({R['self_rows']} row). Distance = square "
         "root of the sum of the eight distance pieces; each piece = measure weight x (his standard score - "
         "comparable's standard score)^2. Weight = EXP(-(distance^2) / (2 x yardstick^2)). Rows are sorted by "
         "weight. 'After valuation date' marks profiles or yearly changes from seasons that had not been "
         f"played by {P['trade_date']}: production draws its comparables from the full 2007-2025 data, so "
         "these later seasons do inform the valuation (a documented look-ahead limitation).", 20)
    wc.row_dimensions[2].height = 75
    # target row
    put(wc, "A4", f"{P['name']} (the target)", BOLD)
    feats_lab = [STYLE_LABELS[f][0] for f in ac.FEATS]
    header(wc, 5, 6, ["Target standard score: " + x for x in feats_lab])
    for j in range(8):
        pr_ = R["prof_rows"][j]
        put(wc, f"{CL(6 + j)}6", "=" + ref(wp, f"G{pr_}"), GREEN, N3)
    n = len(R["comps"])
    top, bot = 11, 11 + n - 1
    steps = R["step_rows"]
    # summary block
    put(wc, "A7", "Sum of comparable weights", BOLD)
    put(wc, "E7", f"=SUM($AF${top}:$AF${bot})", BLACK, N3)
    put(wc, "A8", "Effective number of comparables", BOLD)
    put(wc, "E8", f"=SUM($AF${top}:$AF${bot})^2/SUMPRODUCT($AF${top}:$AF${bot},$AF${top}:$AF${bot})", BLACK, "0.0")
    wc["E8"].comment = Comment("(sum of weights)^2 / sum of squared weights: how many equally weighted "
                               "comparables would carry the same information.", "walkthrough")
    put(wc, "G7", "Share of weight on the 5 closest", BOLD)
    put(wc, "K7", f"=SUM($AF${top}:$AF${top + 4})/E7", BLACK, "0.0%")
    put(wc, "G8", "Share of weight on profiles after valuation date", BOLD)
    put(wc, "K8", f"=SUMPRODUCT($AF${top}:$AF${bot},$E${top}:$E${bot})/E7", BLACK, "0.0%")
    cols = (["Rank", "Comparable", "Profile seasons", "Age", "After valuation date (1 = yes)"]
            + [f"Value: {x}" for x in feats_lab] + [f"Standard score: {x}" for x in feats_lab]
            + [f"Distance piece: {x}" for x in feats_lab]
            + ["Distance", "Distance in yardsticks", "Weight", "Share of total weight"])
    for sr_ in steps:
        cols += [f"Change in WAR per 82, age {sr_['from_age']} to {sr_['to_age']}",
                 f"That change after valuation date (1 = yes)"]
    widths = [6, 22, 18, 5, 10] + [11] * 24 + [10, 10, 9, 9] + [12, 10] * len(steps)
    header(wc, 10, 1, cols, widths)
    wc.row_dimensions[10].height = 75
    for i, c in enumerate(R["comps"]):
        q_ = top + i
        put(wc, f"A{q_}", i + 1, BLACK, "0")
        put(wc, f"B{q_}", c["display"], BLUE)
        put(wc, f"C{q_}", c["seasons"], BLUE)
        put(wc, f"D{q_}", c["age"], BLUE, "0")
        put(wc, f"E{q_}", c["after"], BLUE, "0")
        for j in range(8):
            vc, zc, pc_ = CL(6 + j), CL(14 + j), CL(22 + j)
            mr = MEAS["row0"] + j
            put(wc, f"{vc}{q_}", float(c["X"][j]), BLUE, N4)
            put(wc, f"{zc}{q_}", f"=({vc}{q_}-Settings!$D${mr})/Settings!$E${mr}", BLACK, N3)
            put(wc, f"{pc_}{q_}", f"=Settings!$B${mr}*({zc}{q_}-{CL(6 + j)}$6)^2", BLACK, N4)
        put(wc, f"AD{q_}", f"=SQRT(SUM(V{q_}:AC{q_}))", BLACK, N3)
        put(wc, f"AE{q_}", f"=AD{q_}/Yardstick", BLACK, N2)
        # parentheses matter: Excel reads -AD^2 as (-AD)^2, which would turn every weight above 1
        put(wc, f"AF{q_}", f"=EXP(-(AD{q_}^2)/(2*Yardstick^2))", BLACK, N4, KEY_FILL)
        put(wc, f"AG{q_}", f"=AF{q_}/$E$7", BLACK, "0.00%")
        for k_, sr_ in enumerate(steps):
            dv, aft = c["steps"][sr_["from_age"]]
            cc, fc = CL(34 + 2 * k_), CL(35 + 2 * k_)
            if dv is not None:
                put(wc, f"{cc}{q_}", dv, BLUE, N3)
                put(wc, f"{fc}{q_}", aft, BLUE, "0")
    wc.freeze_panes = "C11"
    R["comp_range"] = (wc, top, bot)

    # =========== 4 Aging path ===========
    wa = wb.create_sheet(f"{s} 4 Aging path")
    wa.column_dimensions["A"].width = 58
    for c_ in "BCDEFGHIJ":
        wa.column_dimensions[c_].width = 14
    put(wa, "A1", f"{P['name']}: from comparables to projected WAR", TITLE)
    W_ = f"'{wc.title}'!$AF${top}:$AF${bot}"
    LV = f"'{wc.title}'!$L${top}:$L${bot}"          # the comparables' production-level measure
    put(wa, "A3", "Step A. Pull his starting curve level toward 'players like him'", BOLD)
    note(wa, "A4", "The aging curve runs in WAR per 82 games. It starts from his own two-season level, then pulls "
         f"{int(round((1 - ac.LAMBDA) * 100))}% of the way toward the weighted level of his comparables. That "
         "comparable level is itself blended with the league average for forwards of his age, which counts as "
         "if it were one more comparable carrying K_league units of weight.", 6)
    wa.row_dimensions[4].height = 60
    lines = [
        ("His own level (WAR per 82, two-season average)", f"={R['cell_lvl']}", GREEN, N4),
        ("Comparables' weighted level (their own production-level measure)", f"=SUMPRODUCT({W_},{LV})/SUM({W_})", BLACK, N4),
        ("Sum of comparable weights", f"=SUM({W_})", BLACK, N3),
        (f"League average level, forwards aged {ba}", R["glevel"], BLUE, N4),
        ("Weight on the league average", "=K_league", GREEN, "0.0"),
        ("'Players like him' level = (weighted comparables + league) / total weight",
         "=(SUMPRODUCT({W},{L})+B11*B10)/(B9+B11)".format(W=W_, L=LV), BLACK, N4),
        ("Share of that level coming from the comparables", "=B9/(B9+B11)", BLACK, "0.0%"),
        ("Share kept from his own level", "=Lambda", GREEN, N2),
        (f"Starting curve level at age {ba} = kept x own + (1 - kept) x players-like-him", "=B14*B7+(1-B14)*B12",
         BLACK, N4),
    ]
    for i, (lb, f_, font, fmt) in enumerate(lines):
        put(wa, f"A{7 + i}", lb).alignment = WRAP
        put(wa, f"B{7 + i}", f_, font, fmt, KEY_FILL if i in (5, 8) else None)
    wa["B10"].comment = Comment("AgingModel.glevel: average two-season level of every forward season at this "
                                "age in the panel.", "walkthrough")

    put(wa, "A18", "Step B. Walk the curve forward one year at a time", BOLD)
    note(wa, "A19", "Each year's change is the weighted average of what his comparables' production did over that "
         "same year of age, using only comparables still playing at both ages, again blended with the league "
         "average change for forwards of that age. The weights are the same ones set at age "
         f"{ba}; comparables who drop out simply stop contributing (the count falls).", 9)
    wa.row_dimensions[19].height = 60
    header(wa, 21, 1, ["From age", "To age", "Comparables with both seasons", "Their total weight",
                       "Comparables' weighted change", "League average change", "Change used",
                       "Curve level (WAR per 82)", "Share of weight from changes after valuation date"])
    wa.column_dimensions["A"].width = 58
    put(wa, "H22", "=B15", BLACK, N4)
    put(wa, "A22", f"start (age {ba})")
    for k_, sr_ in enumerate(steps):
        q_ = 23 + k_
        D_ = f"'{wc.title}'!${CL(34 + 2 * k_)}${top}:${CL(34 + 2 * k_)}${bot}"
        A_ = f"'{wc.title}'!${CL(35 + 2 * k_)}${top}:${CL(35 + 2 * k_)}${bot}"
        put(wa, f"A{q_}", sr_["from_age"], BLACK, "0")
        put(wa, f"B{q_}", sr_["to_age"], BLACK, "0")
        put(wa, f"C{q_}", f"=SUMPRODUCT(ISNUMBER({D_})*1)", BLACK, "0")
        put(wa, f"D{q_}", f"=SUMPRODUCT({W_},ISNUMBER({D_})*1)", BLACK, N3)
        put(wa, f"E{q_}", f"=IF(D{q_}>0,SUMPRODUCT({W_},{D_})/D{q_},NA())", BLACK, N4)
        put(wa, f"F{q_}", sr_["league"], BLUE, N4)
        put(wa, f"G{q_}", f"=(SUMPRODUCT({W_},{D_})+K_league*F{q_})/(D{q_}+K_league)", BLACK, N4, KEY_FILL)
        put(wa, f"H{q_}", f"=H{q_ - 1}+G{q_}", BLACK, N4)
        put(wa, f"I{q_}", f"=IF(D{q_}>0,SUMPRODUCT({W_},{A_})/D{q_},NA())", BLACK, "0.0%")
    last_step_row = 22 + len(steps)

    c0 = last_step_row + 3
    put(wa, f"A{c0}", "Step C. Turn the curve into projected WAR for each contract season", BOLD)
    note(wa, f"A{c0 + 1}", "The curve is used only for its SHAPE. Each season's multiplier = curve level that season "
         f"/ curve level in the valuation season (age {ag}). Projected WAR = starting level (a season total, "
         "sheet 1) x multiplier, with the multiplier kept between RatioFloor and RatioCap. If the curve level in "
         "the valuation season is at or below BaseFloor, the projection holds flat. The valuation season "
         "itself always has multiplier 1.", 9)
    wa.row_dimensions[c0 + 1].height = 60
    header(wa, c0 + 3, 1, ["Contract season", "Age", "Curve level (WAR per 82)", "Multiplier (raw)",
                           "Multiplier used", "Starting level (WAR)", "Projected WAR",
                           "Hindsight: actual games", "Hindsight: actual WAR (season-length adjusted)"])
    R["proj_rows"] = []
    base_cell = None
    for k_, so in enumerate(R["seasons"]):
        q_ = c0 + 4 + k_
        R["proj_rows"].append(q_)
        put(wa, f"A{q_}", so["season"])
        put(wa, f"B{q_}", so["age"], BLACK, "0")
        # curve level at this age; if the walk stopped before this age, hold the last level
        put(wa, f"C{q_}", f"=IFERROR(INDEX($H$22:$H${last_step_row},MATCH(B{q_},$B$22:$B${last_step_row},0)),"
            f"$H${last_step_row})", BLACK, N4)
        if k_ == 0:
            base_cell = f"$C${q_}"
        put(wa, f"D{q_}", f"=C{q_}/{base_cell}", BLACK, N4)
        put(wa, f"E{q_}", f"=IF({base_cell}<=BaseFloor,1,MIN(MAX(D{q_},RatioFloor),RatioCap))", BLACK, N4)
        put(wa, f"F{q_}", f"={R['cell_anchor']}", GREEN, N3)
        # D12 v3: a negative starting level keeps its own value in the valuation season, then 0 WAR
        neg = f"F{q_}" if k_ == 0 else "0"
        put(wa, f"G{q_}", f"=IF(F{q_}>=0,F{q_}*E{q_},{neg})", BLACK, N3, KEY_FILL, bold=True)
        rw = R["row_of"].get(int(so["season"][:4]))
        if rw:
            put(wa, f"H{q_}", f"={ref(R['ws_seasons'], f'D{rw}')}", GREEN, "0", HIND_FILL)
            put(wa, f"I{q_}", f"={ref(R['ws_seasons'], f'N{rw}')}", GREEN, N3, HIND_FILL)
    # the curve beyond the last step (only if the walk stopped early): note, not a formula
    note(wa, f"A{c0 + 5 + len(R['seasons'])}", "Hindsight columns are for comparison only; the model never sees "
         "them. The projection is a forecast of his production if he keeps playing; the separate exit "
         "probabilities (not shown here) handle the chance he does not.", 9)
    R["ws_aging"] = wa


def build_readme(ws, results):
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 110
    put(ws, "A1", "Aging curve walkthrough: three traded forwards", TITLE)
    rows = [
        ("What this is", "The production aging curve worked through with real data for three forwards, each valued "
         "on the day he was traded. Every number is either copied from the source data (blue) or computed by an "
         "Excel formula you can inspect (black). Change a setting on the Settings sheet and everything updates."),
        ("Built by", f"{SCRIPT_VERSION}. Its hand arithmetic was checked against the production code "
         "(aging_curve.py, skater_forward_projection.py) before this file was written, and this file's formula "
         "results were checked against it after recalculation."),
        ("Players", "; ".join(f"{R['P']['name']} ({R['P']['trade']}, {R['P']['trade_date']}, valued as of "
                              f"{season_label(R['P']['t0'])})" for R in results)),
        ("Sheets, per player", "1 Seasons: his WAR by season and the starting level. 2 Profile: his eight "
         "comparison measures. 3 Comparables: every eligible comparable, its distance and weight. "
         "4 Aging path: how the weights become a curve and the curve becomes projected WAR."),
        ("Shared sheets", "Settings: every constant the formulas use. Yardstick: how the shared yardstick is "
         "built and how distance becomes weight."),
        ("Colours", "Blue text: data copied from source files or from the production code. Black: formulas. "
         "Green: links to another sheet. Yellow fill: key results and settings. Grey rows: seasons after the "
         "valuation date, shown for hindsight only."),
        ("WAR", "Wins above replacement from Patrick Bacon's public model. A season total unless a column says "
         "'per 82 games' (WAR / games x 82)."),
        ("Not included", "Dollars, cap hits, exit probabilities and discounting. This file covers the aging curve only."),
    ]
    for i, (a, b) in enumerate(rows):
        put(ws, f"A{3 + i}", a, BOLD).alignment = WRAP
        put(ws, f"B{3 + i}", b).alignment = WRAP
        ws.row_dimensions[3 + i].height = 45


# ---------------------------------------------------------------------------
# RECALCULATE AND CHECK THE WORKBOOK AGAINST PYTHON
# ---------------------------------------------------------------------------
def recalc_and_check(results, h):
    """LibreOffice computes every formula; then each key result is compared
    with the Python value that already passed the production guards."""
    recalc = os.environ.get("XLSX_RECALC")
    if not (recalc and Path(recalc).exists()):
        return check_with_formulas_engine(results)
    if recalc and Path(recalc).exists():
        out = subprocess.run([sys.executable, recalc, str(OUT_XLSX), "900"], capture_output=True, text=True)
        txt = out.stdout
        info = json.loads(txt[txt.find("{"): txt.rfind("}") + 1]) if "{" in txt else {}
        assert info.get("status") == "success", f"workbook recalculation failed: {out.stdout} {out.stderr}"
        log(f"  workbook recalculated: {info.get('total_formulas')} formulas, 0 errors")
    from openpyxl import load_workbook
    wb = load_workbook(OUT_XLSX, data_only=True)
    worst = 0.0
    for R in results:
        s = R["P"]["short"]
        wc = wb[f"{s} 3 Comparables"]
        for i, c in enumerate(R["comps"]):
            v = wc[f"AF{11 + i}"].value
            worst = max(worst, abs(v - c["w"]))
        wa = wb[f"{s} 4 Aging path"]
        checks = [(wa["B12"].value, R["norm"]), (wa["B15"].value, R["start"])]
        for k_, sr_ in enumerate(R["step_rows"]):
            checks.append((wa[f"G{23 + k_}"].value, sr_["step"]))
        for k_, so in enumerate(R["seasons"]):
            checks.append((wa[f"G{R['proj_rows'][k_]}"].value, so["projected_war"]))
        ws1 = wb[f"{s} 1 Seasons"]
        checks.append((ws1[R["cell_anchor"].split("!")[1].replace("$", "")].value, R["anchor"]))
        for got, want in checks:
            assert got is not None, f"{s}: a checked formula has no value after recalculation"
            worst = max(worst, abs(got - want))
    assert worst < 1e-9, f"workbook formulas differ from Python by {worst}"
    log(f"  guard (f) workbook formula results match Python (max abs diff {worst:.1e})")


def check_with_formulas_engine(results):
    """Guard (f) without LibreOffice: the `formulas` package evaluates the
    saved workbook with Excel's own operator rules (it caught a -x^2
    precedence bug that Python arithmetic cannot). Values are compared, the
    workbook itself is left untouched, so Excel still computes on open."""
    try:
        import formulas
    except ImportError:
        log("  guard (f) SKIPPED: neither XLSX_RECALC nor the `formulas` package is available "
            "(pip install formulas). Excel computes every formula when the file is opened.")
        return
    sol = formulas.ExcelModel().loads(str(OUT_XLSX)).finish().calculate()
    book = OUT_XLSX.name.upper()
    vals = {}
    for k, v in sol.items():
        try:
            vals[k.upper()] = v.value[0, 0]
        except (AttributeError, IndexError, TypeError):
            continue

    def g(sheet, cell):
        return vals.get(f"'[{book}]{sheet.upper()}'!{cell}")
    errs = [k for k, v in vals.items() if type(v).__name__ == "XlError"]
    assert not errs, f"workbook formula errors: {errs[:10]}"
    worst = 0.0
    for R in results:
        s = R["P"]["short"]
        checks = [(g(f"{s} 3 Comparables", f"AF{11 + i}"), c["w"]) for i, c in enumerate(R["comps"])]
        checks += [(g(f"{s} 4 Aging path", "B12"), R["norm"]), (g(f"{s} 4 Aging path", "B15"), R["start"])]
        checks += [(g(f"{s} 4 Aging path", f"G{23 + k_}"), sr_["step"]) for k_, sr_ in enumerate(R["step_rows"])]
        checks += [(g(f"{s} 4 Aging path", f"G{R['proj_rows'][k_]}"), so["projected_war"])
                   for k_, so in enumerate(R["seasons"])]
        checks.append((g(f"{s} 1 Seasons", R["cell_anchor"].split("!")[1].replace("$", "")), R["anchor"]))
        for got, want in checks:
            assert got is not None, f"{s}: a checked formula has no value"
            worst = max(worst, abs(float(got) - want))
    assert worst < 1e-9, f"workbook formulas differ from Python by {worst}"
    log(f"  guard (f) workbook formulas evaluated with Excel operator rules ({len(vals)} cells, 0 errors); "
        f"key results match Python (max abs diff {worst:.1e})")


# ---------------------------------------------------------------------------
LABELS = {}
AGES_ALL = {}


def main():
    global LABELS, AGES_ALL
    log(SCRIPT_VERSION)
    log(f"inputs: {F_WAR_AGE} sha256 {sha(F_WAR_AGE)[:16]}")
    log(f"        {F_WAR} sha256 {sha(F_WAR)[:16]}")
    log(f"        aging_curve.py sha256 {sha(REPO / '20_CODE' / 'aging_curve.py')[:16]}")
    log(f"        skater_forward_projection.py sha256 "
        f"{sha(REPO / '20_CODE' / 'skater_forward_projection.py')[:16]}")
    assert PRORATION == {2019: 82 / 70, 2020: 82 / 56}, "season-length factors changed; review before use"

    m = AgingModel(str(F_WAR_AGE))
    log(f"aging model: {len(m.players)} careers, {len(m.names)} comparable profiles, "
        f"yardstick {m.h:.4f}, lambda {ac.LAMBDA}")
    h, pooled, per_pos, pct = yardstick(m)
    assert h == m.h, f"recomputed yardstick {h} != AgingModel.h {m.h}"
    log(f"  guard (a) yardstick recomputed exactly: {h:.6f} "
        f"(forwards {per_pos['F']['profiles_sampled']} sampled, defence {per_pos['D']['profiles_sampled']})")

    LABELS, AGES_ALL = curve_season_labels()
    full = (OUTPUT_DIR / "contract_season_spine.csv").exists()
    if full:
        sp = sfp.SkaterProjector()
        sp.curve = m
        log("mode: FULL (contract spine found; production anchor and contract chain are checked too)")
    else:
        sp = light_projector(m)
        log("mode: LIGHT (no contract spine on this machine; anchor, age and horizon cross-checks skipped)")

    results = []
    for P in PLAYERS:
        log(f"\n{P['name']} (valued {season_label(P['t0'])}, traded {P['trade_date']})")
        R = walk(m, sp, full, P, LABELS)
        R["same_age_median"], R["same_age_n"] = same_age_median(m, R["pos"], R["base_age"])
        log(f"  starting level {R['anchor']:.3f} WAR; age {R['age']} (curve based at {R['base_age']}); "
            f"{len(R['comps'])} comparables, effective {R['eff_n']:.1f}, top-5 share {R['top5_share']:.1%}")
        log(f"  own level {R['sm_level']:.3f} -> players-like-him {R['norm']:.3f} -> start {R['start']:.3f} "
            f"(WAR per 82)")
        log("  projected WAR: " + ", ".join(f"{s['season']} {s['projected_war']:.2f}" for s in R["seasons"]))
        results.append(R)

    build_workbook(m, (h, pooled, per_pos, pct), results)
    recalc_and_check(results, h)

    # ---- numbers for the explainer ----------------------------------------
    js = dict(version=SCRIPT_VERSION, mode="full" if full else "light",
              war_with_age_sha256=sha(F_WAR_AGE), yardstick=h, yardstick_groups=per_pos,
              yardstick_percentiles=pct, n_profiles=int(len(m.names)), careers=len(m.players),
              players=[])
    for R in results:
        js["players"].append(dict(
            name=R["P"]["name"], trade=R["P"]["trade"], trade_date=R["P"]["trade_date"],
            valuation_season=season_label(R["P"]["t0"]), age=R["age"], base_age=R["base_age"],
            profile_seasons=[season_label(y) for y in R["win_years"]],
            anchor=R["anchor"], anchor_source=R["anchor_src"], last_season=R["w1"], season_before=R["w2"],
            profile=dict(zip(ac.FEATS, map(float, R["raw"]))),
            standard_scores=dict(zip(ac.FEATS, map(float, R["tz"]))),
            n_comparables=len(R["comps"]), sum_weights=R["sum_w"], effective_n=R["eff_n"],
            top5_share=R["top5_share"], share_weight_profiles_after=R["after_share"],
            n_profiles_after=R["n_after"],
            same_age_yardstick=R["same_age_median"], same_age_profiles=R["same_age_n"],
            top10=[dict(name=c["display"], seasons=c["seasons"], distance=c["d"], yardsticks=c["d"] / h,
                        weight=c["w"], share=c["w"] / R["sum_w"], after=c["after"],
                        pieces=dict(zip(ac.FEATS, map(float, c["contrib"]))),
                        values=dict(zip(ac.FEATS, map(float, c["X"]))))
                   for c in R["comps"][:10]],
            own_level=R["sm_level"], league_level=R["glevel"], players_like_him=R["norm"],
            start_curve_level=R["start"], steps=R["step_rows"], seasons=R["seasons"], path=R["path"]))
    OUT_JSON.write_text(json.dumps(js, indent=2, default=float))
    log(f"\nwrote {OUT_XLSX}\nwrote {OUT_JSON}")
    OUT_LOG.write_text("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
