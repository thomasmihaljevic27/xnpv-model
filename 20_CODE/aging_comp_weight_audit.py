"""What the aging curve's comparable weights actually do, by player level.

Run from the repository root. Read-only: it fits the production `AgingModel`
and inspects its weights. It writes one CSV and prints three tables. Nothing in
`30_OUTPUT/` that the chain reads is touched, and no production constant moves.

WHY THIS EXISTS
---------------
`aging_curve.py` forms a player's anchor as

    compnorm = (sum(w_i * L_i) + SHRINK_K * glevel[pos, age]) / (sum(w_i) + SHRINK_K)
    anchor   = LAMBDA * own_smoothed_level + (1 - LAMBDA) * compnorm

with w_i = exp(-d_i^2 / (2h^2)) and h the median within-position pairwise
distance. Two questions about that get asked repeatedly and neither can be
answered from the constants alone:

  1. How much weight does the broad position-and-age average (the SHRINK_K
     term) really take, and does it take more for unusual players?
  2. How comparable is the "comparable" side? A Gaussian kernel whose
     bandwidth is the median pairwise distance of the whole cloud is close to
     flat, and a flat kernel returns the cohort average with a slight tilt
     rather than an estimate built from similar players.

This script measures both, so the answer is a number rather than an inference
from the source. THE RETENTION SLOPE IS THE HEADLINE: the share of a player's
deviation from his position-and-age cell that survives into the comparable
estimate. 1.0 would mean the estimate tracks the player; 0.0 would mean it is
the cell average regardless of who he is.

WHAT IT REPORTS
---------------
  A. Fitted bandwidth, and the retention implied for a Gaussian kernel on a
     unit-variance pool, 1/(1+h^2). The measured slope sits above this because
     level correlates with ice time and role, so similar-level players are
     close on several axes at once.
  B. Retention slope by position, before and after the SHRINK_K pooling, so the
     two levers are separated. The gap between the two columns is ALL that
     changing SHRINK_K can buy.
  C. Comparable-set quality by level band: the share of comparable weight
     coming from players within HALF A WIN per 82 of the target, and the Kish
     effective number of comparables against the raw pool size. An effective
     count close to the pool size means the kernel is not selecting.

READ IT WITH THIS CAVEAT
------------------------
Pool size varies sharply with AGE -- a peak-age cell is large, an 18- or
38-year-old cell is small -- and SHRINK_K's share is driven by pool size. So
the same elite player can sit in a cell where the pooled term is negligible at
27 and material at 37, which is the back half of exactly the long contracts
elite players sign. The per-age table is written to the CSV for that reason;
the printed band table pools ages and hides it.

USAGE
-----
    python 20_CODE/aging_comp_weight_audit.py

REQUIRES `OUTPUT_DIR/WAR_with_age.csv` from `age_join.py`, which needs the
PuckPedia birthdate export. That export is confidential vendor data and is not
in the repository.
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd

from aging_curve import AgingModel, _profile, SHRINK_K, LAMBDA

SCRIPT_VERSION = '1.0'
OUT = Path(os.environ['OUTPUT_DIR'])
# Fixed bands in WAR per 82 games, declared here rather than taken from sample
# quantiles so repeated runs on different vintages stay comparable.
BANDS = [(-np.inf, 0.0, 'neg'), (0.0, 1.0, 'lo'), (1.0, 2.0, 'mid'),
         (2.0, 3.0, 'high'), (3.0, np.inf, 'elite')]
SIMILAR = 0.5           # "actually comparable" = within this many WAR/82


def audit(model):
    """One row per target season, holding what the weights did for that target."""
    rows = []
    for name, p in model.players.items():
        ss = p['seasons']
        for i, s in enumerate(ss):
            age = s['age']
            # Same profile construction the projection uses, including the
            # review-item-1.7 fallback when the previous season is not adjacent.
            lo = i if not p['adjacent'].get(age, False) else max(0, i - 1)
            own = p['sm'][age]
            mu, sd = model.stats[p['pos']]
            z = ((_profile(ss[lo:i + 1], own) - mu) / sd) * np.sqrt(model.fw)
            # exclude=name mirrors project()'s default: a player is never his
            # own comparable.
            cand, w = model._weights(z, p['pos'], age, exclude=name)
            if cand is None or not len(cand) or w.sum() <= 0:
                continue
            col = model.Lser[cand, age - model.AMIN]
            observed = ~np.isnan(col)          # _shrunk masks to these
            ww = w * observed
            if ww.sum() <= 0:
                continue
            vals = np.where(observed, col, 0.0)
            comp_only = float(np.nansum(ww * vals) / ww.sum())          # SHRINK_K = 0
            glob = model.glevel.get((p['pos'], age), own)
            compnorm = float((np.nansum(ww * vals) + SHRINK_K * glob) / (ww.sum() + SHRINK_K))
            near = observed & (np.abs(np.nan_to_num(col) - own) <= SIMILAR)
            rows.append(dict(
                player=name, pos=p['pos'], age=age, own_level=own,
                comp_only=comp_only, compnorm=compnorm,
                cell_mean=float(np.nanmean(col[observed])),
                weight_sum=float(ww.sum()),
                # what the fixed pooling weight is actually worth here
                global_share=float(SHRINK_K / (ww.sum() + SHRINK_K)),
                share_weight_from_similar=float(ww[near].sum() / ww.sum()),
                # Kish effective sample size: how many comparables the kernel
                # is really using, as against how many are in the pool.
                effective_comps=float(ww.sum() ** 2 / np.sum(ww ** 2)),
                pool=int(observed.sum()), similar_in_pool=int(near.sum())))
    return pd.DataFrame(rows)


def retention(d, col):
    """Slope of the estimate on the player's own level, centred WITHIN age cell.

    Centring within the cell is the point: it removes the age profile, so the
    slope answers 'how much of THIS player, rather than his cohort, survives'.
    """
    x = d.own_level - d.groupby('age').own_level.transform('mean')
    y = d[col] - d.groupby('age')[col].transform('mean')
    return float((x * y).sum() / (x * x).sum())


def main():
    model = AgingModel()
    d = audit(model)
    d['band'] = pd.cut(d.own_level, [b[0] for b in BANDS] + [np.inf],
                       labels=[b[2] for b in BANDS], right=False)
    d.to_csv(OUT / 'aging_comp_weight_audit.csv', index=False)

    print(f'\nA. bandwidth h = {model.h:.3f}  (h^2 = {model.h ** 2:.2f}), '
          f'SHRINK_K = {SHRINK_K:g}, LAMBDA = {LAMBDA:g}')
    print(f'   implied retention for a Gaussian kernel on a unit-variance pool: '
          f'1/(1+h^2) = {1 / (1 + model.h ** 2):.3f}')
    print(f'   {len(d):,} target seasons, {d.player.nunique():,} careers\n')

    print('B. retention slope: share of a player\'s deviation from his cell that '
          'survives into the estimate')
    print('   (the anchor then keeps LAMBDA + (1-LAMBDA) x slope of that deviation)')
    for pos in sorted(d.pos.unique()):
        g = d[d.pos == pos]
        r0, r1 = retention(g, 'comp_only'), retention(g, 'compnorm')
        a0 = LAMBDA + (1 - LAMBDA) * r0
        a1 = LAMBDA + (1 - LAMBDA) * r1
        print(f'   {pos}  comparables alone {r0:.3f} -> after pooling {r1:.3f}   '
              f'|  anchor keeps {a1:.3f} of the deviation, {a0:.3f} if SHRINK_K were 0')

    print('\nC. what the comparable set looks like, by level band')
    tbl = d.groupby('band', observed=True).agg(
        targets=('player', 'size'), median_own=('own_level', 'median'),
        median_comp_estimate=('compnorm', 'median'),
        pct_weight_from_similar=('share_weight_from_similar', 'median'),
        effective_comps=('effective_comps', 'median'),
        similar_in_pool=('similar_in_pool', 'median'),
        pool=('pool', 'median'),
        global_share=('global_share', 'median'))
    print(tbl.to_string(float_format=lambda x: f'{x:.3f}'))
    print(f'\nwrote {OUT / "aging_comp_weight_audit.csv"} '
          f'(per-age detail, which the band table pools away)')


if __name__ == '__main__':
    print(f'SCRIPT_VERSION={SCRIPT_VERSION}', flush=True)
    main()
