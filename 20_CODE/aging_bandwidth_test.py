"""Compare shared and target-specific similarity scales without changing the model.

Run from repository root. Outputs go to OUTPUT_DIR; no production artifact is
overwritten. The registered comparison is the median target-to-candidate distance
versus AgingModel's shared median. Lambda, feature weights, K, profiles, and
projection rules stay fixed. See the run JSON for hashes and the complete design.
"""
from pathlib import Path
import hashlib
import json
import tempfile
import types
import time
import numpy as np
import pandas as pd
from aging_curve import AgingModel, career_key, _profile, LAMBDA, SHRINK_K
import os

SCRIPT_VERSION = '1.0'
SEED = 20260910
FOLDS = 5
BOOTSTRAPS = 2000
ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ['OUTPUT_DIR'])
SOURCE = OUT / 'WAR_with_age.csv'
PREFIX = 'aging_bandwidth_test'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def target_weights(self, target_z, pos, age, exclude=None):
    """Change only the distance scale; preserve the eligible candidate set.

    A target is never used in its own scale. Folds exclude whole target careers
    from the training bank anyway. A zero/empty median falls back to the shared
    scale, preventing division by zero without selecting a new tuned constant.
    """
    cand = self.by_age.get(age, np.array([], int))
    cand = cand[self.pos[cand] == pos] if len(cand) else cand
    if not len(cand):
        return cand, None
    dist = np.sqrt(((self.Zw[cand] - target_z) ** 2).sum(1))
    eligible = self.names[cand] != exclude if exclude is not None else np.ones(len(cand),bool)
    h = float(np.median(dist[eligible])) if eligible.any() else self.h
    if not np.isfinite(h) or h <= 1e-12:
        h = self.h
    w = np.exp(-dist ** 2 / (2 * h ** 2))
    w[~eligible] = 0.0
    return cand, w


def truncated_player(p, age):
    """Allow production project() access only to target history at the origin."""
    q = dict(p)
    q['seasons'] = [s for s in p['seasons'] if s['age'] <= age]
    for k in ['raw','sm','adjacent']:
        q[k] = {a:v for a,v in p[k].items() if a <= age}
    return q


def forecast_pair(model, name, p, age, horizon):
    """Call the existing project() implementation under each weighting rule."""
    assert name not in model.players and name not in set(model.names)
    if p['pos'] not in model.stats or not model.AMIN <= age < model.AMIN+model.nages-1:
        return None
    horizon = min(horizon, model.AMIN+model.nages-1-age)
    target = truncated_player(p,age)
    model.players[name] = target
    original_weights = model._weights
    try:
        shared = model.project(name,age,horizon)
        # Independently reconstruct the shared weights as a reproduction guard.
        ss=target['seasons'];idx=len(ss)-1
        lo=idx if not target['adjacent'].get(age,False) else max(0,idx-1)
        raw=_profile(ss[lo:idx+1],target['sm'][age])
        mu,sd=model.stats[p['pos']];z=((raw-mu)/sd)*np.sqrt(model.fw)
        cand,w=original_weights(z,p['pos'],age,exclude=name)
        if len(cand):
            dist=np.sqrt(((model.Zw[cand]-z)**2).sum(1))
            assert np.allclose(w,np.exp(-dist**2/(2*model.h**2)),atol=1e-14)
            target_h=float(np.median(dist))
            weak=target_h/model.h >= 2.0  # specified before observing errors
            weight_shared=float(w.sum())
        else:
            target_h=model.h;weak=False;weight_shared=0.0
        model._weights=types.MethodType(target_weights,model)
        _,tw=model._weights(z,p['pos'],age,exclude=name)
        tailored=model.project(name,age,horizon)
        assert shared.age.tolist()==tailored.age.tolist()
        meta=dict(shared_h=model.h,target_h=target_h,weak_match=weak,
                  candidate_n=len(cand),weight_shared=weight_shared,
                  weight_target=float(tw.sum()) if tw is not None else 0.0)
        a=dict(zip(shared.age,shared.projected_war_per_82))
        b=dict(zip(tailored.age,tailored.projected_war_per_82))
        return a,b,meta
    finally:
        model._weights=original_weights
        del model.players[name]


def ratio_prediction(levels, age, baseline, horizon):
    """Mirror the production age-1 branch for future contract seasons.

    The curve origin is the last observed season. Valuation is age+1, and
    horizon>=2 is a later contract season. This endpoint is limited to origins
    with usable aging profiles; it does not claim full contract-panel coverage.
    Negative baselines revert to zero, and the 0.25/0/3 guards are held fixed.
    """
    if baseline < 0:
        return 0.0
    base=levels[age+1]
    ratio=1.0 if base<=0.25 else min(max(levels[age+horizon]/base,0.0),3.0)
    return baseline*ratio


def cluster_summary(df):
    """Paired errors, resampling careers rather than correlated player-seasons.

    The bootstrap conditions on fitted folds; it does not refit the model or
    account fully for overlapping training sets. Intervals are exploratory.
    Negative differences favor the target-specific rule.
    """
    if df.empty:
        return {}
    e0=(df.pred_shared-df.actual).abs();e1=(df.pred_target-df.actual).abs()
    work=pd.DataFrame({'name':df.name,'delta':e1-e0})
    per=work.groupby('name').delta.agg(['sum','count'])
    rng=np.random.default_rng(SEED)
    sums=per['sum'].to_numpy();counts=per['count'].to_numpy();n=len(per)
    boots=[]
    for _ in range(BOOTSTRAPS):
        i=rng.integers(0,n,n);boots.append(sums[i].sum()/counts[i].sum())
    return dict(n=len(df),players=n,mae_shared=float(e0.mean()),mae_target=float(e1.mean()),
                delta=float((e1-e0).mean()),improvement_percent=float((e0.mean()-e1.mean())/e0.mean()*100),
                delta_ci_low=float(np.quantile(boots,.025)),delta_ci_high=float(np.quantile(boots,.975)),
                rmse_shared=float(np.sqrt(np.mean((df.pred_shared-df.actual)**2))),
                rmse_target=float(np.sqrt(np.mean((df.pred_target-df.actual)**2))),
                bias_shared=float((df.pred_shared-df.actual).mean()),
                bias_target=float((df.pred_target-df.actual).mean()))


def main():
    start=time.time()
    hashes={str(p.relative_to(ROOT)):digest(p) for p in [SOURCE,ROOT/'20_CODE/aging_curve.py',ROOT/'20_CODE/skater_forward_projection.py']}
    design=dict(script_version=SCRIPT_VERSION,seed=SEED,folds=FOLDS,bootstraps=BOOTSTRAPS,
        change='h = median target distance to same-age same-position training candidates',
        fixed=dict(lambda_kept=LAMBDA,pooled_weight=SHRINK_K),
        primary='Five-fold whole-career holdout; one-to-six-year raw WAR/82 outcomes with >=20 GP',
        secondary='Season-total projection at one-to-five years after valuation using production ratio guards; same surviving observations',
        temporal='Same whole-career folds, training seasons <= origin year, origins 2017-2022; one-to-three-year curve outcomes',
        limitations=['Contemporary reconstructed data, not vintage snapshots','Observed surviving seasons only; no exit/hazard or dollar test',
          'Primary full-era training includes future seasons of OTHER careers; temporal check removes those',
          'Weights and smoothing constants held fixed; no joint tuning','Bootstrap conditions on fitted folds'],
        input_hashes=hashes)
    # Persist the protocol before model fitting or examining errors.
    (OUT/f'{PREFIX}_design.json').write_text(json.dumps(design,indent=2))
    raw=pd.read_csv(SOURCE);raw['career']=raw.Player.map(career_key)
    raw['year']=raw.Season.str[:2].astype(int)+2000
    # Exclude ambiguous career-age mappings from BOTH arms, including training.
    # This is a test-only exclusion, not a repair to production identity data.
    keys=(raw[raw.age.notna()].groupby(['career','year'],as_index=False)
          .agg(age=('age','first'),GP=('GP','sum')))
    bad=[]
    for name,g in keys[keys.GP>=20].groupby('career'):
        if g.age.duplicated().any() or (g.year-g.age).nunique()>1:
            bad.append(name)
    design['excluded_ambiguous_age_careers']=bad
    print('Test-only ambiguous-age exclusions:',bad,flush=True)
    (OUT/f'{PREFIX}_design.json').write_text(json.dumps(design,indent=2))
    raw=raw[~raw.career.isin(bad)].copy()
    with tempfile.TemporaryDirectory(prefix='aging_clean_') as clean_dir:
        clean_path=Path(clean_dir)/'clean.csv'
        raw.drop(columns=['career','year']).to_csv(clean_path,index=False)
        full=AgingModel(str(clean_path))
    names=sorted(full.players)
    fold={}
    rng=np.random.default_rng(SEED)
    for pos in sorted({p['pos'] for p in full.players.values()}):
        group=np.array([n for n in names if full.players[n]['pos']==pos]);rng.shuffle(group)
        fold.update({str(n):i%FOLDS for i,n in enumerate(group)})
    # Map each observed age to its actual season; assert unique career-age keys.
    obs=(raw[raw.age.notna()].groupby(['career','year'],as_index=False)
         .agg(age=('age','first'),GP=('GP','sum'),WAR=('WAR','sum'),pos=('Position','last')))
    age_to_year={}
    # Match production's exclusion of known merged-name careers.
    obs = obs[obs.career.isin(full.players)].copy()
    for name,g in obs.groupby('career'):
        good=g[g.GP>=20]
        assert not good.age.duplicated().any(),f'duplicate career-age: {name}'
        age_to_year[name]={int(r.age):int(r.year) for r in good.itertuples()}
    # Season-total endpoint retains missed games and only adjusts short schedules.
    prod=obs[obs.GP>=10].copy()
    prod['total']=prod.WAR*prod.year.map({2019:82/70,2020:82/56}).fillna(1.0)
    totals={(r.career,int(r.year)):float(r.total) for r in prod.itertuples()}
    rows=[];diagnostics=[]
    with tempfile.TemporaryDirectory(prefix='aging_bandwidth_') as td:
        for mode in ['career_holdout','historical_window']:
            years=[None] if mode=='career_holdout' else list(range(2017,2023))
            for year in years:
                for f in range(FOLDS):
                    train=raw[raw.career.map(fold).ne(f)].copy()
                    if year is not None:train=train[train.year<=year]
                    training_path=Path(td)/'training.csv';train.drop(columns=['career','year']).to_csv(training_path,index=False)
                    model=AgingModel(str(training_path))
                    train_names=set(model.players)
                    assert not any(fold.get(n)==f for n in train_names)
                    for name in names:
                        if fold[name]!=f:continue
                        p=full.players[name];ss=p['seasons']
                        for s in ss[1:]:
                            age=s['age'];origin=age_to_year[name][age]
                            if year is not None and origin!=year:continue
                            horizon=6 if year is None else 3
                            fut=[a for a in p['raw'] if 1<=a-age<=horizon]
                            if not fut:continue
                            # Position at the forecast origin, not at career end.
                            actual_pos=obs[(obs.career==name)&(obs.year==origin)].pos.iloc[0]
                            target=dict(p);target['pos']=actual_pos
                            pair=forecast_pair(model,name,target,age,max(fut)-age)
                            if pair is None:continue
                            a,b,meta=pair
                            info=dict(mode=mode,fold=f,name=name,pos=actual_pos,origin=origin,age=age,star=s['w82']>=3,**meta)
                            diagnostics.append(info)
                            recent=totals.get((name,origin));prior=totals.get((name,origin-1))
                            baseline=.6*recent+.4*prior if recent is not None and prior is not None else recent if recent is not None else prior
                            for fa in fut:
                                if fa not in a:continue
                                h=fa-age
                                assert age_to_year[name][fa]==origin+h
                                rows.append(dict(**info,endpoint='curve',horizon=h,actual=p['raw'][fa],pred_shared=a[fa],pred_target=b[fa]))
                                if h>=2 and age+1 in a and baseline is not None:
                                    actual=totals.get((name,origin+h))
                                    if actual is not None:
                                        rows.append(dict(**info,endpoint='season_total',horizon=h-1,actual=actual,
                                            pred_shared=ratio_prediction(a,age,baseline,h),pred_target=ratio_prediction(b,age,baseline,h)))
                    print(f'{mode} cutoff={year} fold={f}: cumulative {len(rows)} outcomes',flush=True)
    df=pd.DataFrame(rows);diag=pd.DataFrame(diagnostics)
    assert np.isfinite(df[['actual','pred_shared','pred_target']].to_numpy()).all()
    assert not df.duplicated(['mode','endpoint','name','origin','horizon']).any()
    df.to_csv(OUT/f'{PREFIX}_predictions.csv',index=False)
    diag.to_csv(OUT/f'{PREFIX}_origins.csv',index=False)
    results=[]
    for (mode,endpoint),g in df.groupby(['mode','endpoint']):
        selections=[('all',g)]+[(f'horizon_{h}',v) for h,v in g.groupby('horizon')]
        selections += [(f'position_{p}',v) for p,v in g.groupby('pos')]
        selections += [('weak_matches',g[g.weak_match]),('other_matches',g[~g.weak_match]),('stars',g[g.star])]
        selections += [(f'fold_{f}',v) for f,v in g.groupby('fold')]
        for label,part in selections:
            if len(part):results.append(dict(mode=mode,endpoint=endpoint,group=label,**cluster_summary(part)))
    result=pd.DataFrame(results);result.to_csv(OUT/f'{PREFIX}_summary.csv',index=False)
    assert all(digest(ROOT/k)==v for k,v in hashes.items()),'Input or production code changed during test'
    design['elapsed_seconds']=time.time()-start
    design['rows']=len(df);design['origins']=len(diag);design['players']=df.name.nunique()
    (OUT/f'{PREFIX}_run.json').write_text(json.dumps(design,indent=2))
    print(result[result.group=='all'].to_string(index=False),flush=True)
    print(f'Complete in {time.time()-start:.1f}s; production files unchanged.',flush=True)


if __name__=='__main__':
    print(f'SCRIPT_VERSION={SCRIPT_VERSION}',flush=True)
    main()
