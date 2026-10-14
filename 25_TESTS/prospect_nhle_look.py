"""
prospect_nhle_look.py -- does a prospect's production, adjusted to NHL terms, add to his slot? (report only)

ASKED (Thomas, 2026-10-14): "let's investigate how we may be able to include NHLe production." The first
addition to step one (MODEL_DIRECTIVES directive 6). Nothing here is adopted; each choice below is put to
Thomas as an option with what it costs.

THE MEASURE (choices made for this look, each one an option for Thomas)
  * A season's NHLe scoring rate: Elite Prospects skater seasons (ep_skater_seasons, 34 leagues), points
    times the league-season's NHLe factor (nhle_temporal.csv, Bacon/TopDownHockey), summed over his teams that
    season and divided by his games, per 82 games. A season counts with 10+ games (the player model's MIN_GP).
  * 2012-13 has no NHLe factor (the lockout season): the mean of the league's 2011-12 and 2013-14 factors.
    A league-season with no factor (russia2, vhl, mhl in early seasons) leaves those games out.
  * His level: 50/30/20 over the three seasons before the valuation season (most recent first), rescaled over
    the seasons he has (62.5/37.5 with two). No counting season in those three: "no production record".
  * Skaters only. NHLe measures scoring; goalies stay on the slot alone here.

THE ROWS: prospect_slot_years_check.py's rows (drafted 2007-2017, a prospect at k seasons since the draft,
outcome his remaining surplus), skaters only, identical for every arm (asserted by fingerprint).

THE ARMS (each fitted for each k group 0, 1, 2, 3, 4+; through zero, draft-year indicators summing to zero, as
the pick curve):
  slot             surplus = b x star chance                          (step one, on skaters)
  production       surplus = c x NHLe level + m x no-record           (no slot: the undrafted prospect's form)
  slot+production  surplus = b x star chance + c x NHLe level + m x no-record
  slot+production by position: c split for forwards and defencemen
  slot+production curved: adds the NHLe level squared (an elite scorer worth more than in proportion)
  production curved: the same without the slot
  CHOSEN (Thomas, 2026-10-14): curved; seasons 0-2 slot+production curved, 3 and later production curved

SCORING (the pick curve's rule, 2026-10-09): held-out error in dollars on drafts left out of the fit, one draft
at a time, all k groups pooled; then 2,000 redraws of the eleven drafts, counting the redraws where an arm's
summed squared error is below the slot arm's. The pick curve's bar was 1,950 of 2,000; it is reported against,
not applied (no bar is declared for this look).

TRAILING WEIGHTING CHECK (directive 6): the NHLe level reads 50/30/20 (W_NHLE below), rescaled over the seasons he
has. The surplus carries the pick curve's arbitration price (the forecast's 50/30/20).

INPUTS: OUTPUT_DIR/prospect_slot_years_rows.csv (prospect_slot_years_check.py), ep_out/ep_prospects.db,
SOURCE_DIR/nhle_temporal.csv. OUTPUTS: OUTPUT_DIR/prospect_nhle_look.csv, prospect_nhle_rows.csv,
prospect_nhle_look_log.txt.
Run from the repo root:  python 25_TESTS/prospect_nhle_look.py
"""

import hashlib
import os
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv

SCRIPT_VERSION = "prospect_nhle_look.py v1.1 (2026-10-14)"
load_dotenv()
SOURCE_DIR, OUTPUT_DIR = Path(os.environ["SOURCE_DIR"]), Path(os.environ["OUTPUT_DIR"])
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


log(SCRIPT_VERSION)
F = {"rows": OUTPUT_DIR / "prospect_slot_years_rows.csv", "ep": OUTPUT_DIR / "ep_out" / "ep_prospects.db",
     "nhle": SOURCE_DIR / "nhle_temporal.csv"}
for k, p in F.items():
    log(f"  input {k}: {p.resolve()}  (modified {pd.Timestamp(p.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M})")

MIN_GP = 10                       # a season counts with 10+ games (forecast_config.MIN_GP)
W_NHLE = (0.5, 0.3, 0.2)          # 50/30/20, most recent season first
N_REDRAW, SEED = 2000, 20261014

# ---- NHLe factors, 2012-13 filled from its neighbours ----------------------------------------------
nh = pd.read_csv(F["nhle"])
fac = {(r.league, int(r.season_start_year)): float(r.nhle) for r in nh.itertuples()}
filled = 0
for lg in nh["league"].unique():
    if (lg, 2012) not in fac and (lg, 2011) in fac and (lg, 2013) in fac:
        fac[(lg, 2012)] = (fac[(lg, 2011)] + fac[(lg, 2013)]) / 2
        filled += 1
log(f"  NHLe 2012-13 filled as the mean of 2011-12 and 2013-14 for {filled} leagues")

# ---- each player's NHLe season rates ---------------------------------------------------------------
con = sqlite3.connect(F["ep"])
s = pd.read_sql("select ep_player_id, season, league, gp, tp from ep_skater_seasons", con)
s["syr"] = s["season"].str[:4].astype(int)
s["ep_player_id"] = pd.to_numeric(s["ep_player_id"]).astype(int).astype(str)   # same key type as the rows
s["gp"], s["tp"] = pd.to_numeric(s["gp"], errors="coerce"), pd.to_numeric(s["tp"], errors="coerce")
s = s[(s["gp"] > 0) & s["tp"].notna()].copy()
s["f"] = [fac.get((lg, y)) for lg, y in zip(s["league"], s["syr"])]
log(f"  EP skater rows with games: {len(s):,}; without an NHLe factor (left out): {int(s['f'].isna().sum()):,}")
s = s[s["f"].notna()]
s["nhle_pts"] = s["tp"] * s["f"]
season = s.groupby(["ep_player_id", "syr"]).agg(gp=("gp", "sum"), nhle_pts=("nhle_pts", "sum"))
season = season[season["gp"] >= MIN_GP]
season["rate82"] = season["nhle_pts"] / season["gp"] * 82
RATE = season["rate82"].to_dict()

# ---- the rows ---------------------------------------------------------------------------------------
draft = pd.read_sql("select draft_year draftYear, draft_overall pick, ep_player_id, position_ep from ep_draft_selections", con)
d = pd.read_csv(F["rows"])
d = d[d["prospect"] & ~d["is_goalie"].astype(bool)].merge(draft, on=["draftYear", "pick"], how="left")
assert d["ep_player_id"].notna().all()
d["ep_player_id"] = pd.to_numeric(d["ep_player_id"]).astype(int).astype(str)


def level(ep, y):
    got = [(w, RATE[(ep, z)]) for w, z in zip(W_NHLE, (y - 1, y - 2, y - 3)) if (ep, z) in RATE]
    return (sum(w * r for w, r in got) / sum(w for w, _ in got), len(got)) if got else (0.0, 0)


lv = [level(e, y) for e, y in zip(d["ep_player_id"], d["season"])]
d["nhle82"], d["n_seasons"] = [x[0] for x in lv], [x[1] for x in lv]
d["no_record"] = (d["n_seasons"] == 0).astype(float)
d["is_d"] = d["position_ep"].astype(str).str.startswith("D").astype(float)
d["k_group"] = d["k"].map(lambda k: str(k) if k < 4 else "4+")
assert d["no_record"].mean() < 0.5, "the production join failed"   # GUARD (v1.0 first run: 100% unmatched, a key-type bug)
FP = hashlib.sha1(pd.util.hash_pandas_object(d[["draftYear", "pick", "k"]], index=False).values).hexdigest()[:12]
log(f"\nrows: {len(d):,} skater prospect-rows ({d[['draftYear', 'pick']].drop_duplicates().shape[0]:,} players); "
    f"fingerprint {FP}; no production record: {int(d['no_record'].sum()):,} ({d['no_record'].mean():.1%})")
log("  NHLe points per 82 (50/30/20), by seasons since the draft (rows with a record):")
for g, x in d[d["n_seasons"] > 0].groupby("k_group"):
    log(f"    {g:>2}: n {len(x):5,}  median {x['nhle82'].median():5.1f}  90th pct {x['nhle82'].quantile(.9):5.1f}  "
        f"corr with star chance {np.corrcoef(x['nhle82'], x['p_star'])[0, 1]:.2f}")

ARMS = {"slot": ["p_star"], "production": ["nhle82", "no_record"],
        "slot+production": ["p_star", "nhle82", "no_record"],
        "slot+production by position": ["p_star", "nhle_f", "nhle_d", "no_record"],
        "slot+production curved": ["p_star", "nhle82", "nhle82_sq", "no_record"],
        "production curved": ["nhle82", "nhle82_sq", "no_record"]}
d["nhle_f"], d["nhle_d"] = d["nhle82"] * (1 - d["is_d"]), d["nhle82"] * d["is_d"]
d["nhle82_sq"] = d["nhle82"] ** 2 / 10        # per 10 (points per 82) squared, so its coefficient reads on the same scale


def design(frame, cols, classes):
    yrs = frame["draftYear"].values
    return np.column_stack([frame[c].values for c in cols]
                           + [(yrs == c).astype(float) - (yrs == classes[-1]).astype(float) for c in classes[:-1]])


def fit(frame, cols, cluster):
    cl = sorted(frame["draftYear"].unique())
    X = design(frame, cols, cl)
    if cluster:
        groups = pd.factorize(frame["draftYear"].astype(str) + "-" + frame["pick"].astype(str))[0]
        return sm.OLS(frame["remaining_M"].values, X).fit(cov_type="cluster", cov_kwds={"groups": groups})
    return sm.OLS(frame["remaining_M"].values, X).fit(cov_type="HC1")


def predict_out(train, test, cols, cluster):
    """Fit without the held-out draft; predict it at the average draft (its own year effect unknown)."""
    m = fit(train, cols, cluster)
    return test[cols].values @ m.params[:len(cols)]


# ---- coefficients on all drafts, and held-out errors ---------------------------------------------------
coef_rows, err = [], {a: np.zeros(len(d)) for a in ARMS}
d = d.reset_index(drop=True)
for g, x in d.groupby("k_group"):
    clus = g == "4+"
    for a, cols in ARMS.items():
        m = fit(x, cols, clus)
        coef_rows.append({"k_group": g, "arm": a, **{f"{c}": m.params[i] for i, c in enumerate(cols)},
                          **{f"{c}_se": m.bse[i] for i, c in enumerate(cols)}})
        for c in sorted(x["draftYear"].unique()):
            tr, te = x[x["draftYear"] != c], x[x["draftYear"] == c]
            err[a][te.index] = te["remaining_M"].values - predict_out(tr, te, cols, clus)
co = pd.DataFrame(coef_rows)

log("\nCOEFFICIENTS ON ALL DRAFTS ($M of remaining surplus; NHLe level in points per 82 games; se in brackets)")
for g in ["0", "1", "2", "3", "4+"]:
    for a in ARMS:
        r = co[(co["k_group"] == g) & (co["arm"] == a)].iloc[0]
        parts = [f"{c} {r[c]:.3f} ({r[c + '_se']:.3f})" for c in ARMS[a]]
        log(f"  {g:>2} {a:<28} " + "; ".join(parts))

# ---- scores --------------------------------------------------------------------------------------------
cls = sorted(d["draftYear"].unique())
rng = np.random.default_rng(SEED)
draws = [rng.choice(cls, size=len(cls), replace=True) for _ in range(N_REDRAW)]
sse_by = {a: d.assign(e2=err[a] ** 2).groupby("draftYear")["e2"].sum() for a in ARMS}
n_by = d.groupby("draftYear").size()
log("\nHELD-OUT ERROR (each draft predicted from a fit without it; $M of remaining surplus a row; same rows for every arm)")
out = []
for a in ARMS:
    rmse = float(np.sqrt(np.mean(err[a] ** 2)))
    by_k = {g: float(np.sqrt(np.mean(err[a][x.index] ** 2))) for g, x in d.groupby("k_group")}
    wins = int(sum(sse_by[a][list(dr)].sum() < sse_by["slot"][list(dr)].sum() for dr in draws)) if a != "slot" else None
    out.append({"arm": a, "rmse_M": rmse, **{f"rmse_k{g}": v for g, v in by_k.items()}, "redraws_beating_slot": wins,
                "rows": len(d), "fingerprint": FP})
    log(f"  {a:<28} RMSE {rmse:.4f}  by k: " + ", ".join(f"{g} {v:.4f}" for g, v in by_k.items())
        + ("" if wins is None else f"  | beats the slot in {wins:,} of {N_REDRAW:,} redraws"))

# ---- the combination Thomas chose (2026-10-14): curved; seasons 0-2 slot + production, 3+ production alone ----
early = d["k_group"].isin(["0", "1", "2"]).values
err["chosen"] = np.where(early, err["slot+production curved"], err["production curved"])
sse_by["chosen"] = d.assign(e2=err["chosen"] ** 2).groupby("draftYear")["e2"].sum()
for a, base in (("chosen", "slot"), ("chosen", "slot+production curved")):
    wins = int(sum(sse_by[a][list(dr)].sum() < sse_by[base][list(dr)].sum() for dr in draws))
    log(f"  CHOSEN (curved; slot + production for seasons 0-2, production alone from 3) RMSE "
        f"{np.sqrt(np.mean(err[a] ** 2)):.4f}; beats {base} in {wins:,} of {N_REDRAW:,} redraws")
by_k = {g: float(np.sqrt(np.mean(err["chosen"][x.index] ** 2))) for g, x in d.groupby("k_group")}
log("    by k: " + ", ".join(f"{g} {v:.4f}" for g, v in by_k.items()))
out.append({"arm": "chosen", "rmse_M": float(np.sqrt(np.mean(err["chosen"] ** 2))),
            **{f"rmse_k{g}": v for g, v in by_k.items()},
            "redraws_beating_slot": int(sum(sse_by["chosen"][list(dr)].sum() < sse_by["slot"][list(dr)].sum() for dr in draws)),
            "rows": len(d), "fingerprint": FP})

# ---- what it means for one prospect --------------------------------------------------------------------
log("\nWHAT IT MEANS (slot+production, all drafts): a pick at #20 (star chance from the rows) one season after the draft")
r1 = co[(co["k_group"] == "1") & (co["arm"] == "slot+production")].iloc[0]
p20 = float(d.loc[d["pick"] == 20, "p_star"].iloc[0])
for lv_ in (d.loc[(d["k_group"] == "1") & (d["n_seasons"] > 0), "nhle82"].quantile([.25, .5, .75, .9])).items():
    log(f"  NHLe level at the {int(lv_[0] * 100)}th percentile of one-season-on prospects ({lv_[1]:.1f} per 82): "
        f"${r1['p_star'] * p20 + r1['nhle82'] * lv_[1]:.2f}M  (slot alone ${co[(co['k_group'] == '1') & (co['arm'] == 'slot')].iloc[0]['p_star'] * p20:.2f}M)")

pd.DataFrame(out).to_csv(OUTPUT_DIR / "prospect_nhle_look.csv", index=False)
co.to_csv(OUTPUT_DIR / "prospect_nhle_coefficients.csv", index=False)
d.to_csv(OUTPUT_DIR / "prospect_nhle_rows.csv", index=False)
(OUTPUT_DIR / "prospect_nhle_look_log.txt").write_text("\n".join(LOG), encoding="utf-8")
log(f"\nwrote prospect_nhle_look.csv, prospect_nhle_coefficients.csv, prospect_nhle_rows.csv and the log in {OUTPUT_DIR}")
