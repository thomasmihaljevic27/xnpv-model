"""
pick_star_form_test.py -- the shape of the dollars-on-star-chance line.

WHY (Thomas, 2026-10-09)
-------------------------------------------------------------------
The pick curve prices a pick on Bacon's star probability for its slot alone
(draft_slot_baseline.csv `p_star`; his definition, hockeystats.com/draft/guide,
read 2026-10-09: career WAR per 82 games of 1.8+ for forwards, 1.23+ for
defencemen; his slot baseline is a logistic regression on pick number with a
kink at pick 150). Thomas asked what function-form questions remain. With
one input there are two: does the line need an intercept, and is it straight?

THE VERSIONS, by numbers fitted (draft-year effects aside; they are fitted in
every version as sum-to-zero indicators, so "no intercept" means the AVERAGE
draft year passes through zero)
  1  origin    surplus = b x P(star)                 (a no-star pick is worth zero)
  2  line      surplus = a + b x P(star)             (the version chosen 2026-10-09)
  3  quad      surplus = a + b x P(star) + c x P(star)^2
  3  power     surplus = a + b x P(star)^k           (k fitted)

SCORING AND RULE: as pick_curve_shape_test.py, declared before the run.
Leave one draft class out; mean squared miss in $M over held-out picks; 2,000
redraws of the eleven classes (seed 20261009). The one-number version stands
unless a version with more numbers has a lower mean squared miss than EVERY
simpler version in at least 1,950 of 2,000 redraws (Thomas's bar).

INPUTS: OUTPUT_DIR/pick_first_look_players.csv (v1.1), SOURCE_DIR/
draft_slot_baseline.csv.

Run from the repo root:  python 25_TESTS/pick_star_form_test.py
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from scipy.optimize import minimize_scalar

SCRIPT_VERSION = "pick_star_form_test.py v1.0 (2026-10-09)"
BAR, N_DRAWS, SEED = 1950, 2000, 20261009
print(SCRIPT_VERSION)
print(f"  rule: more numbers must beat every simpler version in >= {BAR} of {N_DRAWS} class redraws")
load_dotenv()
OUT, SRC = Path(os.environ["OUTPUT_DIR"]), Path(os.environ["SOURCE_DIR"])
F_PL, F_LOG, F_B = OUT / "pick_first_look_players.csv", OUT / "pick_first_look_log.txt", SRC / "draft_slot_baseline.csv"
for p in (F_PL, F_LOG, F_B):
    print(f"  input: {p.resolve()}  (modified {pd.Timestamp(p.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M})")
assert F_LOG.read_text(encoding="utf-8").startswith("pick_regression_first_look.py v1.1")

bacon = pd.read_csv(F_B)[["draft_pick", "p_star"]]
d = pd.read_csv(F_PL).merge(bacon, left_on="pick", right_on="draft_pick", validate="many_to_one")
d["y"] = d["surplus"] / 1e6
CLASSES = sorted(d["draftYear"].unique())


def year_cols(years, classes):
    """Sum-to-zero indicators: one column per class but the last; the last class is -1 in every column."""
    X = np.zeros((len(years), len(classes) - 1))
    for j, c in enumerate(classes[:-1]):
        X[:, j] = (years == c).astype(float)
    X[years == classes[-1], :] = -1.0
    return X


def ols(cols, y):
    beta, *_ = np.linalg.lstsq(cols, y, rcond=None)
    return beta


def fit(version, tr):
    """Return a function P(star) -> $M at the average draft year, plus the fitted slot numbers."""
    cl = sorted(tr["draftYear"].unique())
    Y = year_cols(tr["draftYear"].values, cl)
    p, y = tr["p_star"].values, tr["y"].values
    one = np.ones((len(tr), 1))
    if version == "origin":
        b = ols(np.column_stack([p, Y]), y)
        return (lambda q: b[0] * q), {"b": b[0]}
    if version == "line":
        b = ols(np.column_stack([one, p, Y]), y)
        return (lambda q: b[0] + b[1] * q), {"a": b[0], "b": b[1]}
    if version == "quad":
        b = ols(np.column_stack([one, p, p ** 2, Y]), y)
        return (lambda q: b[0] + b[1] * q + b[2] * q ** 2), {"a": b[0], "b": b[1], "c": b[2]}
    if version == "power":
        def sse(k):
            X = np.column_stack([one, p ** k, Y])
            return np.sum((y - X @ ols(X, y)) ** 2)
        k = minimize_scalar(sse, bounds=(0.2, 3.0), method="bounded").x
        b = ols(np.column_stack([one, p ** k, Y]), y)
        return (lambda q: b[0] + b[1] * q ** k), {"a": b[0], "b": b[1], "k": k}
    raise ValueError(version)


VERSIONS = {"origin": 1, "line": 2, "quad": 3, "power": 3}
sq = {v: np.empty(len(d)) for v in VERSIONS}
for c in CLASSES:
    te = d["draftYear"].values == c
    for v in VERSIONS:
        f, _ = fit(v, d[~te])
        sq[v][te] = (d["y"].values[te] - f(d["p_star"].values[te])) ** 2

print("\nHELD-OUT MISS ($M a pick) and each version fitted on all eleven classes")
at = [1, 2, 3, 5, 10, 20, 32, 64, 100, 150, 200]
q = bacon.set_index("draft_pick").loc[at, "p_star"].values
rows = {}
for v, n in VERSIONS.items():
    f, par = fit(v, d)
    rows[v] = {"numbers": n, "RMSE": np.sqrt(sq[v].mean()), "MAE": np.sqrt(sq[v]).mean(),
               "fit": ", ".join(f"{k} {x:.3f}" for k, x in par.items()),
               **{f"#{a}": f(qq) for a, qq in zip(at, q)}}
tab = pd.DataFrame(rows).T
print(tab[["numbers", "RMSE", "MAE", "fit"]].to_string())
print("\n$M at an average draft year")
print(tab[[f"#{a}" for a in at]].astype(float).round(2).to_string())

rng = np.random.default_rng(SEED)
idx = {c: np.flatnonzero(d["draftYear"].values == c) for c in CLASSES}
mse = {v: np.empty(N_DRAWS) for v in VERSIONS}
for i in range(N_DRAWS):
    ii = np.concatenate([idx[c] for c in rng.choice(CLASSES, size=len(CLASSES), replace=True)])
    for v in VERSIONS:
        mse[v][i] = sq[v][ii].mean()
wins = pd.DataFrame({a: {b: int((mse[a] < mse[b]).sum()) if a != b else np.nan for b in VERSIONS}
                     for a in VERSIONS}).T
print(f"\nREDRAWS WON (row beats column, of {N_DRAWS})")
print(wins.to_string(float_format=lambda v: f"{v:.0f}"))

current = "origin"
for n in (2, 3):
    simpler = [v for v, k in VERSIONS.items() if k < n]
    ok = [v for v, k in VERSIONS.items() if k == n and all(wins.loc[v, s] >= BAR for s in simpler)]
    for v in [v for v, k in VERSIONS.items() if k == n]:
        print(f"  {v} ({n}) against simpler: " + ", ".join(f"{s} {int(wins.loc[v, s])}" for s in simpler))
    if ok:
        current = min(ok, key=lambda v: tab.loc[v, "RMSE"])
print(f"\nVERDICT under the declared rule: {current}")
