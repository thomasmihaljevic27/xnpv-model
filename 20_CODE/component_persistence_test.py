"""component_persistence_test.py -- how much year-to-year signal does each
Bacon WAR component carry, and does a component-wise, rolling-calibrated
starting point predict future season WAR better than the locked 60/40 blend?

TEST ONLY. Reads WAR.csv, writes four files under OUTPUT_DIR with this
script's name as prefix. Touches no production file. Written 2026-09-14 to
make the scratch diagnostic quoted in the ground-up review reproducible
(the review's comparison rightly noted the figure had no saved code).

WHAT IT MEASURES
  Part 1  Persistence. For every pair of consecutive seasons a player played
          20+ games in both: the correlation of each component's per-82 rate
          with itself the following season, and each component's share of
          the variance of total WAR/82. The share is a COVARIANCE share,
          cov(component, total) / var(total), so the six shares sum to one
          (a plain variance ratio would not, because components co-move;
          that ratio is reported alongside for reference).
  Part 2  Rolling forecast. Standing at valuation season t0 (2016..2025)
          with seasons t0-1 and t0-2 only (the anchor's own information
          set), predict season-total WAR at horizon h = 0, 1, 2, where h=0
          is season t0 itself, the chain's valuation season. Three rules:
            raw   the locked 60/40 blend, unchanged
            L     a + b x blend, plus position and a one-season flag
                  (the pull-back the 2026-09-14 sweep tested)
            comp  a + sum_c b_c x (60/40 blend of component c) + position
                  + games share + one-season flag
          Every rule is fitted only on pairs whose OUTCOME season is before
          t0, so nothing sees the season it predicts. Outcomes are seasons
          the player played 10+ games (the anchor filter); non-participation
          is not scored here -- that is the participation model's job.

ASSUMPTIONS BAKED IN
  * Names cleaned with skater_value_engine.norm_name; team-halves summed
    per (name, position, season) before any filter (review item 1.5).
  * D20 proration on totals and components (x82/70 for 2019-20, x82/56 for
    2020-21) before anything else.
  * MIN_GP = 10 for a season to enter the anchor; 20 for the persistence
    pairs, matching the aging curve's own filter.
  * Fits are ordinary least squares. No shrinkage constant is estimated
    here; the coefficients ARE the pooled shrinkage (share carried forward).
"""
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).resolve().parent))
from skater_value_engine import norm_name, MERGED_WAR_NAMES, PRORATION, MIN_GP, W_T1, W_T2

SCRIPT_VERSION = "1.0"
SOURCE_DIR = Path(os.environ["SOURCE_DIR"])
OUT = Path(os.environ["OUTPUT_DIR"])
PREFIX = "component_persistence_test"
COMP = ["EVO WAR", "EVD WAR", "PP WAR", "PK WAR", "Pens WAR", "Shoot WAR"]
SEASON_LEN = {2019: 70, 2020: 56}
PAIR_MIN_GP = 20
T0_YEARS = list(range(2016, 2026))
HORIZONS = [0, 1, 2]


def season_table():
    w = pd.read_csv(SOURCE_DIR / "WAR.csv")
    w["syr"] = w["Season"].str.split("-").str[0].astype(int) + 2000
    bare = w["Player"].map(norm_name)
    w = w[~bare.isin(MERGED_WAR_NAMES)].copy()
    w["k"] = w["Player"].map(norm_name) + "|" + w["Position"]
    pr = w["syr"].map(PRORATION).fillna(1.0)
    for c in COMP + ["WAR"]:
        w[c] = w[c] * pr
    # GUARD, same rule as skater_value_engine: only where two rows share a key
    # may the summed games exceed 82. (A single source row can already exceed
    # 82 -- the source merges most traded players into one row, e.g. Cody
    # Ceci 24-25 S.J/DAL, 85 GP -- so the check is on duplicated keys only.)
    dup = w.duplicated(["k", "syr"], keep=False)
    if dup.any():
        tot = w[dup].groupby(["k", "syr"])["GP"].sum()
        assert (tot <= 82).all(), f"two players share a key: {list(tot[tot > 82].index)}"
    a = w.groupby(["k", "syr"], as_index=False).agg(
        **{c: (c, "sum") for c in COMP + ["WAR"]}, GP=("GP", "sum"))
    a["pos"] = a["k"].str[-1]
    a["gp_share"] = a["GP"] / a["syr"].map(SEASON_LEN).fillna(82.0)
    for c in COMP + ["WAR"]:
        a[c + "_82"] = a[c] / a["GP"] * 82.0
    return a


def persistence(a):
    b = a[a["GP"] >= PAIR_MIN_GP]
    p = b.merge(b.assign(syr=b["syr"] - 1), on=["k", "syr"], suffixes=("", "_n"))
    tot = p["WAR_82"]
    rows = []
    for c in COMP:
        rows.append(dict(component=c,
                         yoy_r=p[c + "_82"].corr(p[c + "_82_n"]),
                         cov_share_of_war82=np.cov(p[c + "_82"], tot)[0, 1] / tot.var(),
                         var_ratio=p[c + "_82"].var() / tot.var()))
    rows.append(dict(component="WAR total per 82", yoy_r=tot.corr(p["WAR_82_n"]),
                     cov_share_of_war82=1.0, var_ratio=1.0))
    rows.append(dict(component="WAR season total", yoy_r=p["WAR"].corr(p["WAR_n"]),
                     cov_share_of_war82=np.nan, var_ratio=np.nan))
    rows.append(dict(component="games share", yoy_r=p["gp_share"].corr(p["gp_share_n"]),
                     cov_share_of_war82=np.nan, var_ratio=np.nan))
    return pd.DataFrame(rows), len(p)


def features(a):
    """One row per (player, t0): the 60/40 blends from t0-1 / t0-2 (GP>=10),
    plus each horizon's outcome where the player played 10+ games. The blend
    rule is the locked one: both seasons 60/40, one season alone."""
    s = a[a["GP"] >= MIN_GP].set_index(["k", "syr"])
    war = s["WAR"].to_dict()
    rows = []
    for (k, t1), r1 in s.iterrows():
        t0 = t1 + 1
        has2 = (k, t0 - 2) in s.index
        r2 = s.loc[(k, t0 - 2)] if has2 else None
        f = dict(k=k, t0=t0, isd=float(k.endswith("D")), single=float(not has2))

        def blend(col):
            return W_T1 * r1[col] + W_T2 * r2[col] if has2 else r1[col]

        f["blend"] = blend("WAR")
        f["gp"] = blend("gp_share")
        for c in COMP:
            f["b_" + c] = blend(c)
        for h in HORIZONS:
            f[f"y{h}"] = war.get((k, t0 + h), np.nan)
        rows.append(f)
    return pd.DataFrame(rows)


def ols(X, y):
    X = np.column_stack([np.ones(len(y)), X])
    return np.linalg.lstsq(X, y, rcond=None)[0]


COLS = {"L": ["blend", "isd", "single"],
        "comp": ["b_" + c for c in COMP] + ["isd", "gp", "single"]}


def rolling(d):
    out = []
    for h in HORIZONS:
        y = f"y{h}"
        for t0 in T0_YEARS:
            # admissible training: outcome season t0_train + h <= t0 - 1
            tr = d[(d["t0"] + h <= t0 - 1) & d[y].notna()]
            te = d[(d["t0"] == t0) & d[y].notna()]
            if te.empty:
                continue
            err = {"raw": te["blend"] - te[y]}
            for name, cs in COLS.items():
                b = ols(tr[cs].to_numpy(float), tr[y].to_numpy(float))
                err[name] = (b[0] + te[cs].to_numpy(float) @ b[1:]) - te[y]
            hi = te["blend"] >= 3
            row = dict(horizon=h, t0=t0, n=len(te), n_3plus=int(hi.sum()))
            for name, e in err.items():
                row[f"mae_{name}"] = e.abs().mean()
                row[f"bias_{name}"] = e.mean()
                row[f"bias3_{name}"] = e[hi].mean() if hi.any() else np.nan
            out.append(row)
    return pd.DataFrame(out)


def main():
    clock = time.time()
    print(f"SCRIPT_VERSION={SCRIPT_VERSION}", flush=True)
    a = season_table()
    pers, npairs = persistence(a)
    pers.to_csv(OUT / f"{PREFIX}_persistence.csv", index=False)
    print(f"\nPart 1 -- persistence on {npairs:,} consecutive {PAIR_MIN_GP}+ GP season pairs")
    print(pers.round(3).to_string(index=False))
    d = features(a)
    r = rolling(d)
    r.to_csv(OUT / f"{PREFIX}_rolling.csv", index=False)
    summ = []
    for h in HORIZONS:
        x = r[r["horizon"] == h]
        w = x["n"] / x["n"].sum()
        raw = np.average(x["mae_raw"], weights=w)
        rec = dict(horizon=h, n=int(x["n"].sum()), n_3plus=int(x["n_3plus"].sum()), mae_raw=raw)
        for name in ("L", "comp"):
            m = np.average(x[f"mae_{name}"], weights=w)
            rec[f"mae_{name}"] = m
            rec[f"change_{name}_pct"] = 100 * (m / raw - 1)
        w3 = x["n_3plus"].to_numpy(float)
        for name in ("raw", "L", "comp"):
            rec[f"bias3_{name}"] = np.average(x[f"bias3_{name}"].fillna(0), weights=w3)
        summ.append(rec)
    summ = pd.DataFrame(summ)
    summ.to_csv(OUT / f"{PREFIX}_summary.csv", index=False)
    print("\nPart 2 -- rolling out-of-sample MAE of season-total WAR, t0 = 2016..2025, "
          "outcome seasons with 10+ GP (weighted by n); bias3 = mean error for "
          "players whose blend was 3+ WAR:")
    print(summ.round(3).to_string(index=False))
    cs = COLS["comp"]
    ok = d["y0"].notna()
    b = ols(d.loc[ok, cs].to_numpy(float), d.loc[ok, "y0"].to_numpy(float))
    coef = dict(zip(["intercept"] + cs, [float(v) for v in b]))
    print("\nshare of each component's blend carried into the valuation season (h=0, full sample):")
    for kk, v in coef.items():
        print(f"  {kk:14s} {v:+.3f}")
    (OUT / f"{PREFIX}_run.json").write_text(json.dumps(dict(
        script_version=SCRIPT_VERSION, n_pairs=npairs, n_feature_rows=len(d),
        t0_years=T0_YEARS, horizons=HORIZONS, coefficients_h0=coef,
        elapsed_seconds=time.time() - clock), indent=2))
    print(f"\n{time.time() - clock:.0f}s; outputs {PREFIX}_persistence/_rolling/_summary.csv, _run.json")


if __name__ == "__main__":
    main()
