"""Reproduce uncertainty diagnostics and audit their controls at a candidate checkout.

Only development pages are used. --mode uncertainty captures the actual runner's
page-specific calibrators. --mode leakage runs the published battery and repeats
its sensitivity experiment with fitted parameters held fixed. --mode guard checks
the contract-export reproduction guard in its isolated scratch directory.
"""
import argparse
import json
import os
from pathlib import Path
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--candidate-root', type=Path, required=True)
    ap.add_argument('--mode', choices=['uncertainty','leakage','sensitivity','guard'], required=True)
    args = ap.parse_args()
    root = Path(__file__).resolve().parents[2]
    os.environ['SOURCE_DIR'] = str(root/'10_SOURCE')
    os.environ['OUTPUT_DIR'] = str(root/'30_OUTPUT')
    os.environ['PUCKPEDIA_CONTRACTS_XLSX'] = str(root/'10_SOURCE/PuckPedia_Player_Contract_Export_May_22_2026__CONFIDENTIAL.xlsx')
    sys.path.insert(0,str(args.candidate_root.resolve()/'50_REBUILD/code'))
    import numpy as np
    import pandas as pd
    import predictive_interval as PI
    import forecast_harness as H
    import information_set as I
    from ability_forecast import A1HingeExposure
    results = {'candidate': str(args.candidate_root), 'mode':args.mode}
    if args.mode == 'guard':
        import contract_source
        results['guard_passed'] = bool(contract_source.guard_against_locked_regression())
    elif args.mode == 'uncertainty':
        import run_uncertainty as U
        spreads, scored = {}, []
        original_fit, original_run = PI.WithIntervals.fit, H.Harness.run
        def fit(self, table, before):
            out = original_fit(self,table,before)
            spreads[before] = self.spread_
            return out
        def run(self, model, *a, **kw):
            out = original_run(self,model,*a,**kw)
            if isinstance(model,PI.WithIntervals):
                scored.append(out.copy())
            return out
        try:
            PI.WithIntervals.fit, H.Harness.run = fit, run
            U.main()
        finally:
            PI.WithIntervals.fit, H.Harness.run = original_fit, original_run
        d = scored[0]
        pl = d[d.played].copy()
        pl['mu'] = pl.rate_82*pl.gp_share
        pl['z_actual_scale'] = np.nan
        pl['residual_percentile'] = np.nan
        mean_gaps, qs_by_page = [], []
        for (page,h), g in pl.groupby(['page','h']):
            spread = spreads[int(page)]
            z = (g.act_war-g.mu)/spread.sigma(int(h),g.mu)
            pl.loc[g.index,'z_actual_scale'] = z
            pl.loc[g.index,'residual_percentile'] = PI._shape_cdf(z,spread.zs_)
        # A mixture with empirical residual Z has expectation p*(mu+sigma*E[Z]).
        # Integrate the piecewise-linear quantile exactly by trapezoids.
        for page,spread in spreads.items():
            ez = float(np.trapezoid(spread.zs_,dx=1/(len(spread.zs_)-1)))
            qs_by_page.append(dict(page=int(page),mean_z=ez,
                fitted_width80=float(np.diff(np.quantile(spread.zs_,[.1,.9]))[0])))
            for h,g in d[d.page==page].groupby('h'):
                mu = g.rate_82*g.gp_share
                gap = g.p_play*spread.sigma(int(h),mu)*ez
                mean_gaps.extend(gap.tolist())
        results['calibrators'] = qs_by_page
        results['distribution_mean_minus_point'] = dict(mean=float(np.mean(mean_gaps)),
            mean_abs=float(np.mean(np.abs(mean_gaps))),max_abs=float(np.max(np.abs(mean_gaps))))
        shape=[]
        for col in ['tier','age_band']:
            for group,g in pl[pl.h==5].groupby(col,observed=True):
                q=np.quantile(g.z_actual_scale,[.05,.5,.95])
                shape.append(dict(by=col,group=str(group),n=len(g),p05=float(q[0]),
                    median=float(q[1]),p95=float(q[2]),
                    below_fitted_05=float((g.residual_percentile<.05).mean()),
                    above_fitted_95=float((g.residual_percentile>.95).mean())))
        results['corrected_h5_shape'] = shape
        results['actual_page_scale_width80'] = float(np.diff(np.quantile(pl.z_actual_scale,[.1,.9]))[0])
        # Comparing each year's held-out residuals to its own fitted shape
        # remains descriptive; year/sample changes do not isolate overfitting.
        results['width_ratios_by_page'] = []
        for page,g in pl.groupby('page'):
            out_width=float(np.diff(np.quantile(g.z_actual_scale,[.1,.9]))[0])
            fit_width=float(np.diff(np.quantile(spreads[int(page)].zs_,[.1,.9]))[0])
            results['width_ratios_by_page'].append(dict(page=int(page),ratio=out_width/fit_width))
    else:
        import run_leakage_tests as L
        if args.mode == 'leakage':
            L.main()
        table,_ = L._load_table()
        rows=[]
        for page in L.PAGES:
            iset=I.build(table,I.decision_date_for_page(page),t0=page)
            subs=H.subjects_at(iset)
            model=A1HingeExposure()
            model.fit(iset.seasons,before=page)
            base=model.predict(iset,subs,L.HORIZONS)
            latest=int(iset.seasons.syr.max())
            for label,alt in [('shock',L._bump(table.copy(),latest,.5)),
                              ('drop_oldest',table[table.syr!=latest-2])]:
                alt_iset=I.build(alt,I.decision_date_for_page(page),t0=page)
                # Same fitted object and same eligible subjects: only inputs change.
                p=model.predict(alt_iset,subs,L.HORIZONS)
                j=base.merge(p,on=['career_key','h'],suffixes=('','_alt'),validate='one_to_one')
                for h,g in j.groupby('h'):
                    finite = np.isfinite(g.rate_82_alt) & np.isfinite(g.rate_82)
                    if label == 'shock':
                        assert finite.all(), 'shock comparison lost a forecast'
                    rows.append(dict(page=int(page),h=int(h),case=label,n=len(g),
                        n_finite=int(finite.sum()),
                        d_rate=float((g.rate_82_alt-g.rate_82).mean())))
        x=pd.DataFrame(rows)
        results['frozen_model_sensitivity'] = x.groupby(['case','h']).d_rate.mean().reset_index().to_dict('records')
        results['sensitivity_counts'] = x.groupby(['case','h'])[['n','n_finite']].sum().reset_index().to_dict('records')
    out=root/f'50_REBUILD/output/review_uncertainty_{args.mode}.json'
    out.write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps(results,indent=2))


if __name__=='__main__':
    main()
