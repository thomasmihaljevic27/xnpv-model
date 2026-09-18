"""Independent reproduction and targeted probes of goalie candidate e42f57c."""
import argparse
import json
import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT/'50_REBUILD/output/goalie_repair_review'
os.environ['SOURCE_DIR'] = str(ROOT/'10_SOURCE')
os.environ['OUTPUT_DIR'] = str(ROOT/'50_REBUILD/output/integration_production')
os.environ['PUCKPEDIA_CONTRACTS_XLSX'] = str(ROOT/'10_SOURCE/PuckPedia_Player_Contract_Export_May_22_2026__CONFIDENTIAL.xlsx')
sys.path.insert(0, str(CANDIDATE/'50_REBUILD/code'))
sys.path.append(str(Path(sys.base_prefix)/'Lib/site-packages'))
import numpy as np
import pandas as pd
import rebuild_config as C
parser=argparse.ArgumentParser()
parser.add_argument('mode', choices=['setup','run','checks','audit','rfa','mutations'])
args=parser.parse_args()
if args.mode=='setup':
    from contract_source import birthdate_table
    birthdate_table(ROOT/'10_SOURCE/ep_birthdates.csv').to_csv(C.out_path('birthdates.csv'),index=False)
elif args.mode=='run':
    import run_goalie_bakeoff as B
    B.main()
elif args.mode=='checks':
    import repair_checks
    repair_checks.main()
elif args.mode=='rfa':
    import run_control_years as R
    R.main()
elif args.mode=='mutations':
    import inspect
    import repair_checks as RC
    import run_goalie_bakeoff as B
    results={}
    def trial(name,obj,attr,replacement,check):
        saved=getattr(obj,attr)
        setattr(obj,attr,replacement)
        try:
            check(None)
            results[name]='MISSED'
        except (AssertionError,pd.errors.MergeError) as exc:
            results[name]='caught: '+str(exc)
        finally:
            setattr(obj,attr,saved)
    trial('lookalike factory',B,'production_projector',lambda:object(),RC.c31)
    trial('simplified benchmark',B.ProductionProjector,'war_for',
          lambda self,s:B.ProductionRule().fit(self.seasons_,self.t0_).war_for(s),RC.c31)
    source=inspect.getsource(B.paired_bootstrap)
    assert 'keys = ["career_key", "page", "h"]' in source
    namespace=dict(B.__dict__)
    exec(source.replace('keys = ["career_key", "page", "h"]','keys = ["career_key", "h"]'),namespace)
    trial('missing page',B,'paired_bootstrap',namespace['paired_bootstrap'],RC.c32)
    trial('age ignored',B.WorkloadWeightedAging,'predict',B.WorkloadWeighted.predict,RC.c32)
    print(json.dumps(results,indent=2))
    assert all(v.startswith('caught:') for v in results.values())
    (ROOT/'50_REBUILD/output/goalie_repair_mutations.json').write_text(json.dumps(results,indent=2))
else:
    import run_goalie_bakeoff as B
    import goalie_season_table as GST
    import information_set as I
    import forecast_harness as H
    table=GST.build(birthdate_csv=C.out_path('birthdates.csv'),verbose=False,allow_thin_ages=True)
    data=pd.read_csv(C.out_path('goalie_bakeoff.csv'))
    base=data[data.rule==B.ProductionProjector.name]
    comparisons={}
    for name, frame in data.groupby('rule'):
        j=base.merge(frame,on=['career_key','page','h'],suffixes=('_a','_b'),validate='one_to_one')
        bad=base.merge(frame,on=['career_key','h'])
        # Cluster bootstrap uses the SAME cells for each goalie in both arms.
        z=j.assign(delta=j.e_war_b.abs()-j.e_war_a.abs()).groupby('career_key').delta.agg(['sum','count'])
        rng=np.random.default_rng(20260917)
        idx=rng.integers(0,len(z),size=(2000,len(z)))
        gaps=z['sum'].to_numpy()[idx].sum(axis=1)/z['count'].to_numpy()[idx].sum(axis=1)
        comparisons[name]=dict(n=len(j),cartesian_n=len(bad),mae=float(frame.e_war.abs().mean()),
            bias=float(frame.e_war.mean()),paired_bootstrap_win=float((gaps<0).mean()),
            gap_ci=np.quantile(gaps,[.025,.975]).tolist())
    page=2021
    iset=I.build(table,I.decision_date_for_page(page),t0=page)
    subs=H.subjects_at(iset)
    model=B.WorkloadWeightedAging().fit(iset.seasons,page)
    pred=model.predict(iset,subs,[0,5])
    altered=subs.copy(); altered['age']=altered['age']+20
    changed=model.predict(iset,altered,[0,5])
    young=pred[pred.h==5].rate_82.to_numpy()
    result=dict(panel_rows=len(table),goalies=int(table.career_key.nunique()),age_coverage=float(table.has_age.mean()),
        comparisons=comparisons,age_change=model.age_slope_,
        age_intervention_max=float(np.max(np.abs(pred.rate_82-changed.rate_82))),
        missing_age_subjects=int(subs.age.isna().sum()))
    # Compile the actual production projector class, without executing the
    # production module's unrelated startup work. Its lookup uses the same
    # already-aggregated, prorated source panel, including low-GP seasons.
    import ast
    source=CANDIDATE/'20_CODE/contract_npv.py'
    tree=ast.parse(source.read_text(encoding='utf-8-sig'))
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='GoalieProjector')
    spine=pd.read_csv(ROOT/'50_REBUILD/output/integration_production/goalie_value_spine_v2.csv')
    target=float(spine.loc[spine.weight_scheme=='no_observed_war_history','shrunk_projection'].mode().iloc[0])
    ns=dict(np=np,pd=pd,LAMBDA_G=.65,GOALIE_LEAGUE_AVG=target,STALE_TARGET=.650,STALE_MAXBACK=3)
    exec(compile(ast.Module(body=[cls],type_ignores=[]),str(source),'exec'),ns)
    records=[]
    class ActualRule(B.ProductionRule):
        name='actual production projector with shared participation'
        def war_for(self, subjects):
            projector=ns['GoalieProjector'].__new__(ns['GoalieProjector'])
            panel=self.seasons_.copy()
            panel['nname']=panel.pkey.str.rsplit('|',n=1).str[0]
            projector.lut=panel.set_index(['nname','syr']).WAR.sort_index()
            old=super().war_for(subjects)
            values=[]
            for k,r in enumerate(subjects.itertuples()):
                value, path=projector.shrunk_projection(r.pkey.rsplit('|',1)[0],self.t0_)
                values.append(value)
                records.append(dict(page=self.t0_,career_key=r.career_key,actual=value,
                                    labelled=float(old.iloc[k]),path=path))
            return pd.Series(values,index=subjects.career_key)
    actual=H.Harness(table).run(ActualRule(),pages=C.DEV_PAGES,horizons=B.HORIZONS)
    actual.to_csv(ROOT/'50_REBUILD/output/goalie_repair_actual_projector_scored.csv',index=False)
    parity=actual.merge(base,on=['career_key','page','h'],suffixes=('_independent','_imported'),validate='one_to_one')
    result['imported_parity']=dict(n=len(parity),
        max_error_difference=float((parity.e_war_independent-parity.e_war_imported).abs().max()))
    z=base.groupby('career_key').e_war.agg(['sum','count'])
    rng=np.random.default_rng(20260917); idx=rng.integers(0,len(z),size=(2000,len(z)))
    biases=z['sum'].to_numpy()[idx].sum(axis=1)/z['count'].to_numpy()[idx].sum(axis=1)
    result['production_bias']=dict(mean=float(base.e_war.mean()),
        cluster_interval=np.quantile(biases,[.025,.975]).tolist(),
        predicted_play=float(base.p_play.mean()),actual_play=float(base.played.mean()))
    rec=pd.DataFrame(records)
    result['production_parity']=dict(n=len(rec),different=int(((rec.actual-rec.labelled).abs()>1e-6).sum()),
        max_abs=float((rec.actual-rec.labelled).abs().max()),actual_mae=float(actual.e_war.abs().mean()),
        actual_bias=float(actual.e_war.mean()),stale=int((rec.path=='stale_anchor').sum()),
        examples=rec[(rec.actual-rec.labelled).abs()>.5].head(5).to_dict('records'))
    a=data[data.rule==B.ProductionRuleOwnAverage.name]
    b=data[data.rule==B.FittedShrinkage.name]
    j=a.merge(b,on=['career_key','page','h'],suffixes=('_a','_b'),validate='one_to_one')
    z=j.assign(delta=j.e_war_b.abs()-j.e_war_a.abs()).groupby('career_key').delta.agg(['sum','count'])
    rng=np.random.default_rng(20260917); idx=rng.integers(0,len(z),size=(2000,len(z)))
    gaps=z['sum'].to_numpy()[idx].sum(axis=1)/z['count'].to_numpy()[idx].sum(axis=1)
    result['fitted_vs_own_average']=dict(win=float((gaps<0).mean()),ci=np.quantile(gaps,[.025,.975]).tolist())
    j=actual.merge(b,on=['career_key','page','h'],suffixes=('_a','_b'),validate='one_to_one')
    z=j.assign(delta=j.e_war_b.abs()-j.e_war_a.abs()).groupby('career_key').delta.agg(['sum','count'])
    rng=np.random.default_rng(20260917); idx=rng.integers(0,len(z),size=(2000,len(z)))
    gaps=z['sum'].to_numpy()[idx].sum(axis=1)/z['count'].to_numpy()[idx].sum(axis=1)
    result['fitted_vs_actual_projector']=dict(win=float((gaps<0).mean()),
        mean_gap=float((j.e_war_b.abs()-j.e_war_a.abs()).mean()),ci=np.quantile(gaps,[.025,.975]).tolist())
    fitted=B.FittedShrinkage().fit(iset.seasons,page)
    pairs=[]
    for p in range(C.FIRST_SOURCE_SEASON+4,page):
        blend,_=B.trailing_blend(iset.seasons[iset.seasons.syr<p],p)
        nxt=iset.seasons[iset.seasons.syr==p].drop_duplicates('career_key').set_index('career_key').WAR
        pairs.append(pd.concat([blend.rename('x'),nxt.rename('y')],axis=1).dropna())
    training=pd.concat(pairs)
    dx=training.x-fitted.league_; dy=training.y-fitted.league_
    constrained=float(np.clip((dx*dy).sum()/(dx**2).sum(),0,1))
    result['shrinkage_fit']=dict(n=len(training),implemented=fitted.keep_,
        least_squares_for_stated_target=constrained,
        implemented_mse=float(((fitted.keep_*dx-dy)**2).mean()),
        constrained_mse=float(((constrained*dx-dy)**2).mean()))
    projector=B.production_projector()
    saved=projector.lut.copy()
    future_max=0.; subject_count=0
    for p in C.DEV_PAGES:
        info=I.build(table,I.decision_date_for_page(p),t0=p)
        subject=H.subjects_at(info)
        model=B.ProductionProjector().fit(info.seasons,p)
        before=model.war_for(subject)
        projector.lut=saved.copy()
        future=projector.lut.index.get_level_values(1)>=p
        projector.lut.loc[future]=500.
        after=model.war_for(subject)
        future_max=max(future_max,float(np.max(np.abs(before-after))))
        subject_count+=len(subject)
        projector.lut=saved.copy()
    result['future_intervention']=dict(subject_pages=subject_count,max_change=future_max)
    print(json.dumps(result,indent=2))
    (ROOT/'50_REBUILD/output/goalie_repair_audit.json').write_text(json.dumps(result,indent=2))
