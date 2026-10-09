"""
pick_curve_shape_test.py -- which curve shape should value a draft pick?

WHAT THIS DECIDES (MODEL_DIRECTIVES.md directive 6; Thomas, 2026-10-09)
-------------------------------------------------------------------
The pick curve regresses each drafted skater's priced dollars (his surplus
over his control window, from pick_regression_first_look.py v1.1) on his
draft slot. Thomas asked for every offered shape to be tested, favouring the
simpler. Each shape is fitted WITH draft-year indicators (the decided
specification) and predicts a pick at the AVERAGE draft year.

THE SHAPES, by how many numbers they fit for the slot (year effects aside)
  2  line       surplus = a + b x pick
  2  log        surplus = a + b x log(pick)
  3  bend       surplus = a + b x (pick^c - 1)/c   (c fitted; c = 1 is the line,
                c -> 0 is the log, so the data chooses the bend)
  3  logsq      surplus = a + b x log(pick) + d x log(pick)^2
  3  bacon      surplus = a + b x P(NHL player) + d x P(star), Bacon's
                probabilities for that slot (draft_slot_baseline.csv). CAUTION
                (recorded 2026-10-09): his probabilities are fitted on largely
                the same drafts, so this shape partly reads the outcomes.
  4  twopart    surplus = P(plays an NHL game) x E[surplus | he plays]; a
                logit and a regression, each on log(pick) with year effects.
                At the average year the logit's year effects are averaged on
                the logit scale.
  -  benchmark  the average at each pick, forced to fall as the pick number
                rises (isotonic regression on the training classes' means).
                REPORTED ONLY, NEVER ADOPTED: it shows what a formula leaves
                on the table.

HOW A SHAPE IS SCORED (decided 2026-10-09)
  Leave one draft class out: fit on the other ten classes, predict every pick
  in the held-out class, repeat for all eleven. The score is the mean squared
  miss in dollars over all held-out picks (reported as RMSE, with MAE beside
  it). Evidence: 2,000 redraws of the eleven classes with replacement (seed
  20261009), each redraw scoring every shape on the same picks.

THE RULE, DECLARED BEFORE THE RUN (Thomas, 2026-10-09: 1,950 of 2,000)
  1. Among the two-number shapes (line, log), the lower held-out RMSE stands.
  2. A shape with more numbers is adopted only if its mean squared miss is
     lower than EVERY shape with fewer numbers in at least 1,950 of the 2,000
     redraws. Among the three-number shapes that qualify, the lowest RMSE; a
     four-number shape must also clear the bar against every three-number one.
  3. The benchmark is never adopted.
  The script prints the verdict; adopting it is Thomas's decision.

ALSO REPORTED (agreed 2026-10-09): the log curve refitted without the 2017
class (whose 29 short windows were kept), against the curve on all eleven.

INPUTS: OUTPUT_DIR/pick_first_look_players.csv (must come from v1.1, checked
against pick_first_look_log.txt), SOURCE_DIR/draft_slot_baseline.csv.
OUTPUTS: OUTPUT_DIR/pick_curve_shape_test_log.txt, pick_curve_shape_curves.csv.

Run from the repo root:  python 25_TESTS/pick_curve_shape_test.py
"""

import os
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from dotenv import load_dotenv
from scipy.optimize import minimize_scalar
from sklearn.isotonic import IsotonicRegression

SCRIPT_VERSION = "pick_curve_shape_test.py v1.0 (2026-10-09)"
BAR, N_DRAWS, SEED = 1950, 2000, 20261009
load_dotenv()
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
SOURCE_DIR = Path(os.environ["SOURCE_DIR"])
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


log(SCRIPT_VERSION)
log(f"  rule: a shape with more numbers must beat every simpler shape in >= {BAR} of {N_DRAWS} class redraws")
F_PLAYERS = OUTPUT_DIR / "pick_first_look_players.csv"
F_FL_LOG = OUTPUT_DIR / "pick_first_look_log.txt"
F_BACON = SOURCE_DIR / "draft_slot_baseline.csv"
for p in (F_PLAYERS, F_FL_LOG, F_BACON):
    log(f"  input: {p.resolve()}  (modified {pd.Timestamp(p.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M})")
first = F_FL_LOG.read_text(encoding="utf-8").splitlines()[0]
assert first.startswith("pick_regression_first_look.py v1.1"), f"players file is from {first!r}, need v1.1"

d = pd.read_csv(F_PLAYERS)
bacon = pd.read_csv(F_BACON)[["draft_pick", "p_nhler", "p_star"]]
d = d.merge(bacon, left_on="pick", right_on="draft_pick", how="left", validate="many_to_one")
assert d["p_nhler"].notna().all(), "a pick has no Bacon probability"
d["y"] = d["surplus"] / 1e6                      # $M at the 2025-26 cap (scaled partial seasons)
d["log_pick"] = np.log(d["pick"])
d["cls"] = d["draftYear"].astype(str)
d["played"] = (d["nhl_seasons"] > 0).astype(int)
CLASSES = sorted(d["draftYear"].unique())
log(f"  picks {len(d):,} (skaters), classes {CLASSES[0]}-{CLASSES[-1]}; mean ${d['y'].mean():.3f}M")

YR = " + C(cls, Sum)"   # draft-year indicators, sum-to-zero: the intercept is the average-year level


def avg_year(m, terms):
    """Prediction at the average draft year: intercept + slot terms (sum coding)."""
    p = m.params
    return p["Intercept"] + sum(p[k] * v for k, v in terms.items())


def boxcox(pick, c):
    return np.log(pick) if abs(c) < 1e-8 else (pick ** c - 1) / c


# Each fitter takes a training frame and returns a function: test frame -> predictions ($M).
def fit_ols(formula, slot_cols):
    def fitter(tr):
        m = smf.ols(formula + YR, data=tr).fit()
        return lambda te: avg_year(m, {k: te[k].values for k in slot_cols}), m
    return fitter


def fit_bend(tr):
    def sse(c):
        x = tr.assign(bx=boxcox(tr["pick"], c))
        return smf.ols("y ~ bx" + YR, data=x).fit().ssr
    c = minimize_scalar(sse, bounds=(-2.0, 1.5), method="bounded").x
    m = smf.ols("y ~ bx" + YR, data=tr.assign(bx=boxcox(tr["pick"], c))).fit()
    m.bend_c = c
    return (lambda te: m.params["Intercept"] + m.params["bx"] * boxcox(te["pick"].values, c)), m


def fit_twopart(tr):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        lg = smf.logit("played ~ log_pick" + YR, data=tr).fit(disp=0)
    pos = smf.ols("y ~ log_pick" + YR, data=tr[tr["played"] == 1]).fit()

    def pred(te):
        z = lg.params["Intercept"] + lg.params["log_pick"] * te["log_pick"].values
        return 1 / (1 + np.exp(-z)) * (pos.params["Intercept"] + pos.params["log_pick"] * te["log_pick"].values)
    return pred, (lg, pos)


def fit_bench(tr):
    means = tr.groupby("pick")["y"].agg(["mean", "size"])
    iso = IsotonicRegression(increasing=False, out_of_bounds="clip").fit(
        means.index.values, means["mean"].values, sample_weight=means["size"].values)
    return (lambda te: iso.predict(te["pick"].values)), iso


SHAPES = {   # name: (numbers fitted for the slot, fitter)
    "line": (2, fit_ols("y ~ pick", ["pick"])),
    "log": (2, fit_ols("y ~ log_pick", ["log_pick"])),
    "bend": (3, fit_bend),
    "logsq": (3, fit_ols("y ~ log_pick + I(log_pick**2)", ["log_pick", "I(log_pick ** 2)"])),
    "bacon": (3, fit_ols("y ~ p_nhler + p_star", ["p_nhler", "p_star"])),
    "twopart": (4, fit_twopart),
    "benchmark": (None, fit_bench),
}


# logsq's prediction needs the squared column under the name statsmodels gives it
def _with_sq(te):
    return te.assign(**{"I(log_pick ** 2)": te["log_pick"] ** 2})


# ---- leave one class out ------------------------------------------------------
sq = {k: np.empty(len(d)) for k in SHAPES}
ab = {k: np.empty(len(d)) for k in SHAPES}
fold_rmse = []
for c in CLASSES:
    tr, te_mask = d[d["draftYear"] != c], (d["draftYear"] == c).values
    te = _with_sq(d[te_mask])
    row = {"held out": c}
    for k, (_, fitter) in SHAPES.items():
        pred, _ = fitter(tr)
        e = te["y"].values - np.asarray(pred(te))
        sq[k][te_mask], ab[k][te_mask] = e ** 2, np.abs(e)
        row[k] = np.sqrt(np.mean(e ** 2))
    fold_rmse.append(row)

log("\nHELD-OUT MISS, all eleven classes ($M a pick)")
summ = pd.DataFrame({k: {"numbers": SHAPES[k][0] if SHAPES[k][0] else "-",
                         "RMSE": np.sqrt(sq[k].mean()), "MAE": ab[k].mean()} for k in SHAPES}).T
log(summ.to_string(float_format=lambda v: f"{v:.4f}"))
log("\nRMSE by held-out class ($M)")
log(pd.DataFrame(fold_rmse).set_index("held out").round(3).to_string())

# ---- redraws of the eleven classes ----------------------------------------------
rng = np.random.default_rng(SEED)
cls_idx = {c: np.flatnonzero(d["draftYear"].values == c) for c in CLASSES}
draw_mse = {k: np.empty(N_DRAWS) for k in SHAPES}
for i in range(N_DRAWS):
    idx = np.concatenate([cls_idx[c] for c in rng.choice(CLASSES, size=len(CLASSES), replace=True)])
    for k in SHAPES:
        draw_mse[k][i] = sq[k][idx].mean()

names = list(SHAPES)
wins = pd.DataFrame({a: {b: int((draw_mse[a] < draw_mse[b]).sum()) if a != b else np.nan for b in names}
                     for a in names}).T
log(f"\nREDRAWS WON (row beats column on mean squared miss, of {N_DRAWS})")
log(wins.to_string(float_format=lambda v: f"{v:.0f}"))

# ---- the declared rule ---------------------------------------------------------------
rmse = summ["RMSE"].astype(float)
two = [k for k in names if SHAPES[k][0] == 2]
current = min(two, key=lambda k: rmse[k])
log(f"\nRULE step 1: among the two-number shapes, {current} has the lower RMSE "
    f"({rmse[current]:.4f} against {rmse[[k for k in two if k != current][0]]:.4f}; "
    f"lower in {int(wins.loc[current, [k for k in two if k != current][0]])} of {N_DRAWS} redraws)")
for n in (3, 4):
    simpler = [k for k in names if SHAPES[k][0] is not None and SHAPES[k][0] < n]
    for k in [k for k in names if SHAPES[k][0] == n]:
        log(f"  {k} ({n} numbers) against each simpler shape: "
            + ", ".join(f"{s} {int(wins.loc[k, s])}" for s in simpler))
    ok = [k for k in names if SHAPES[k][0] == n and all(wins.loc[k, s] >= BAR for s in simpler)]
    if ok:
        current = min(ok, key=lambda k: rmse[k])
        log(f"RULE step {n - 1}: {', '.join(ok)} clear the bar; {current} adopted at {n} numbers")
    else:
        log(f"RULE step {n - 1}: no {n}-number shape clears {BAR} against every simpler shape")
log(f"\nVERDICT under the declared rule: {current}")
log(f"  benchmark (never adopted) RMSE {rmse['benchmark']:.4f} against {current} {rmse[current]:.4f}: "
    f"the formula leaves {100 * (rmse[current] / rmse['benchmark'] - 1):+.2f}% on the table")

# ---- each shape fitted on all eleven classes ----------------------------------------
grid = pd.DataFrame({"pick": np.arange(1, 218)})
grid["log_pick"] = np.log(grid["pick"])
grid = grid.merge(bacon, left_on="pick", right_on="draft_pick", how="left")
grid = _with_sq(grid)
for k, (_, fitter) in SHAPES.items():
    pred, m = fitter(d)
    grid[k] = np.asarray(pred(grid))
    if k == "bend":
        log(f"\nbend: fitted c = {m.bend_c:.3f} on all classes (1 = straight line, 0 = log)")
at = [1, 2, 3, 5, 10, 15, 20, 32, 64, 100, 150, 200]
raw = d.groupby("pick")["y"].mean()
show = grid.set_index("pick").loc[at, names].copy()
show["raw mean at pick"] = raw.reindex(at).values
log("\nFITTED $M AT AN AVERAGE DRAFT YEAR, all eleven classes")
log(show.round(2).to_string())

# ---- the 2017 check ---------------------------------------------------------------------
pred_all, _ = SHAPES["log"][1](d)
pred_no17, _ = SHAPES["log"][1](d[d["draftYear"] != 2017])
g = grid.set_index("pick").loc[at]
cmp = pd.DataFrame({"all classes": pred_all(g.reset_index()), "without 2017": pred_no17(g.reset_index())},
                   index=at)
cmp["change"] = cmp["without 2017"] - cmp["all classes"]
log("\nLOG CURVE WITH AND WITHOUT THE 2017 CLASS ($M)")
log(cmp.round(3).to_string())

grid.drop(columns=["draft_pick"]).to_csv(OUTPUT_DIR / "pick_curve_shape_curves.csv", index=False)
(OUTPUT_DIR / "pick_curve_shape_test_log.txt").write_text("\n".join(LOG), encoding="utf-8")
log(f"\nwrote pick_curve_shape_curves.csv, pick_curve_shape_test_log.txt in {OUTPUT_DIR}")
