"""Audit the coverage diagnostic on development data; never fit a replacement model."""
import argparse
import json
import os
from pathlib import Path
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--candidate-root', type=Path, required=True)
    ap.add_argument('--reuse-scored', action='store_true')
    args = ap.parse_args()
    root = Path(__file__).resolve().parents[2]
    candidate = args.candidate_root.resolve()
    os.environ['SOURCE_DIR'] = str(root / '10_SOURCE')
    os.environ['OUTPUT_DIR'] = str(root / '30_OUTPUT')
    os.environ['PUCKPEDIA_CONTRACTS_XLSX'] = str(root / '10_SOURCE/PuckPedia_Player_Contract_Export_May_22_2026__CONFIDENTIAL.xlsx')
    sys.path.insert(0, str(candidate / '50_REBUILD/code'))
    import numpy as np
    import rebuild_config as C
    from contract_source import birthdate_table
    import predictive_interval as PI
    import run_coverage_decomposition as D

    birthdate_table(root / '10_SOURCE/ep_birthdates.csv').to_csv(C.out_path('birthdates.csv'), index=False)
    captured = {}
    original = D._prepare
    def capture(s, banded):
        out = original(s, banded)
        captured.update(scored=out, spreads=banded.spreads_)
        return out
    D._prepare = capture
    import pickle
    if args.reuse_scored:
        import pandas as pd
        from types import SimpleNamespace
        s = pd.read_pickle(root / '50_REBUILD/output/coverage_review_scored.pkl')
        with (root / '50_REBUILD/output/coverage_review_shapes.pkl').open('rb') as f:
            spreads = {pg: SimpleNamespace(zs_=zs) for pg, zs in pickle.load(f).items()}
        D._prepare = original
    else:
        try:
            D.main()
        finally:
            D._prepare = original
        s, spreads = captured['scored'], captured['spreads']
    # Preserve row data only in ignored local output to permit independent rechecks.
    s.to_pickle(root / '50_REBUILD/output/coverage_review_scored.pkl')
    with (root / '50_REBUILD/output/coverage_review_shapes.pkl').open('wb') as f:
        pickle.dump({int(pg): sp.zs_ for pg, sp in spreads.items()}, f)
    last = spreads[max(spreads)].zs_
    results = {'candidate': str(candidate), 'rows': len(s), 'shape_differences': [], 'groups': []}
    quantiles = [.05, .1, .5, .9, .95]
    for pg, sp in spreads.items():
        delta = np.quantile(sp.zs_, quantiles) - np.quantile(last, quantiles)
        results['shape_differences'].append(dict(page=int(pg), quantiles=quantiles, difference=delta.tolist()))
    for col, group in D.GROUPS:
        for h in sorted(s.h.unique()):
            g = s[(s[col] == group) & (s.h == h)].copy()
            if len(g) < D.MIN_ROWS:
                continue
            mu, sigma, p = (g[k].to_numpy() for k in ['mu', 'sigma', 'p_play'])
            published = D._levers(g, last)
            covered = []
            for pg, gp in g.groupby('page'):
                cov = D._coverage(gp, spreads[int(pg)].zs_, gp.mu, gp.sigma, gp.p_play)
                covered.append(len(gp) * cov['covered'])
            # Counterexamples to an upper-bound claim, not model proposals:
            # same one-parameter lever, alternative hindsight choices.
            shifts = np.linspace(-2, 2, 161)
            centre_cover = np.array([D._coverage(g, last, mu + sh * sigma, sigma, p)['covered'] for sh in shifts])
            twice = D._coverage(g, last, mu, 2 * sigma, p)['covered']
            # Exact sequential decomposition into COMMON UNITS (WAR).
            # Start with prediction p*r*g, replace p with played indicator,
            # then rate with realized rate, then games share with realized share.
            # Different replacement orders allocate interactions differently.
            pl = g[g.played]
            play_contrib = float(((g.p_play - g.played.astype(float)) * g.mu).mean())
            rate_contrib = float(((pl.rate_82 - pl.act_rate_82) * pl.gp_share).sum() / len(g))
            games_contrib = float((pl.act_rate_82 * (pl.gp_share - pl.act_gp_share)).sum() / len(g))
            # The table caps games share at one. A few traded-player totals
            # exceed its schedule length, leaving a small observable remainder.
            identity_remainder = float((pl.act_rate_82 * pl.act_gp_share - pl.act_war).sum() / len(g))
            total = float(g.e_war.mean())
            assert abs(play_contrib + rate_contrib + games_contrib + identity_remainder - total) < 1e-10
            results['groups'].append(dict(group=group, h=int(h), n=len(g), careers=int(g.career_key.nunique()),
                published_base=published['base']['covered'], own_page_base=sum(covered)/len(g),
                published_centre=published['centre']['covered'],
                best_grid_centre=float(centre_cover.max()), best_grid_shift=float(shifts[centre_cover.argmax()]),
                published_spread=published['spread']['covered'], twice_spread=twice,
                total_bias_WAR=total, sequential_play_WAR=play_contrib,
                sequential_rate_WAR=rate_contrib, sequential_games_WAR=games_contrib,
                observed_identity_remainder_WAR=identity_remainder))
    dest = root / '50_REBUILD/output/review_coverage_decomposition.json'
    dest.write_text(json.dumps(results, indent=2), encoding='utf-8')
    print('\nINDEPENDENT AUDIT\n' + json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
