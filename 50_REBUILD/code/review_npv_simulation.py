"""Audit Phase 5 runner, calibration provenance and simulated dependence."""
import argparse
import json
import os
from pathlib import Path
import pickle
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--candidate-root', type=Path, required=True)
    ap.add_argument('--mode', choices=['run', 'audit'], default='audit')
    args = ap.parse_args()
    root = Path(__file__).resolve().parents[2]
    candidate = args.candidate_root.resolve()
    os.environ['SOURCE_DIR'] = str(root / '10_SOURCE')
    os.environ['OUTPUT_DIR'] = str(root / '30_OUTPUT')
    os.environ['PUCKPEDIA_CONTRACTS_XLSX'] = str(root / '10_SOURCE/PuckPedia_Player_Contract_Export_May_22_2026__CONFIDENTIAL.xlsx')
    sys.path.insert(0, str(candidate / '50_REBUILD/code'))
    import numpy as np
    import pandas as pd
    from scipy import stats
    import npv_simulation as S
    import rebuild_config as C
    capture_path = root / '50_REBUILD/output/simulation_review_seasons.pkl'
    if args.mode == 'run':
        from contract_source import birthdate_table
        import run_npv_simulation as R
        birthdate_table(root / '10_SOURCE/ep_birthdates.csv').to_csv(C.out_path('birthdates.csv'), index=False)
        original = R.per_season
        def capture(*a, **kw):
            result = original(*a, **kw)
            with capture_path.open('wb') as f:
                pickle.dump(result, f)
            return result
        R.per_season = capture
        try:
            R.main()
        finally:
            R.per_season = original
        return

    # Audit uses the immediately preceding local capture and output CSV.
    with capture_path.open('rb') as f:
        seasons, spreads = pickle.load(f)
    last = max(spreads)
    d = pd.read_csv(C.out_path('npv_simulation.csv'))
    result = dict(candidate=str(candidate), global_anchor=int(last),
        latest_residual_outcome=int((spreads[last].pairs_.page + spreads[last].pairs_.h).max()),
        earlier_contracts=sum(seasons[int(i)][0] < last for i in d.contract_id),
        n_contracts=len(d), calibration_by_page=[])
    for pg in sorted(set([min(spreads), 2018, 2021, last]) & set(spreads)):
        sp = spreads[pg]
        def scale(h, mu):
            answer = np.empty(len(h))
            for hz in np.unique(h):
                mask = h == hz
                answer[mask] = sp.sigma(int(hz), mu[mask])
            return answer
        per = S.Persistence().fit(sp.pairs_, scale)
        result['calibration_by_page'].append(dict(page=int(pg), permanent=per.w_perm_,
            fading=per.w_fade_, phi=per.phi_, rho1=float(per.rho(1))))

    p = S.Persistence()
    p.w_perm_, p.w_fade_, p.phi_ = .253, .263, .66
    shape = stats.norm.ppf(np.linspace(.000001, .999999, 10001))
    paths = S.draw_paths([0, 0], [1, 1], [1, 1], shape, p, 600000,
                         np.random.default_rng(1234))
    target = float(p.rho(1))
    result['dependence'] = dict(requested_rank=target,
        realized_rank=float(stats.spearmanr(paths[:, 0], paths[:, 1]).statistic),
        rank_implied_by_gaussian=6 / np.pi * np.arcsin(target / 2))
    try:
        S.self_test(n_paths=600000)
        result['large_sample_self_test'] = 'PASS'
    except AssertionError as exc:
        result['large_sample_self_test'] = str(exc)
    # 60% both, 30% first only, 10% second only: marginals decrease despite returns.
    result['return_counterexample'] = dict(marginals=[.9, .7], return_mass=.1,
        rising_count=S.rising_marginals(np.array([.9, .7])))
    result['reported_outputs'] = dict(mean_gap_dollars=float(d.gap.mean()),
        contract_sign_changes=int((np.sign(d.surplus_point) != np.sign(d.surplus_sim)).sum()),
        one_year_sd_change_pct=float(100 * (d[d.term == 1].sim_sd.mean() /
                                            d[d.term == 1].sd_independent.mean() - 1)))
    out = root / '50_REBUILD/output/review_npv_simulation.json'
    out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
