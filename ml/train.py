"""Train three first-response regressors; held-out seeds cannot influence fitting."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from threadpoolctl import threadpool_limits
from ml.features import FEATURE_COLUMNS, FEATURE_VERSION
from ml.forecast import HORIZONS, trend_prediction, validate_label_step


def split_by_seed(data, train_seeds, validation_seeds, test_seeds):
    partitions=[set(train_seeds),set(validation_seeds),set(test_seeds)]
    if any(a&b for i,a in enumerate(partitions) for b in partitions[i+1:]):
        raise ValueError("seed partitions overlap")
    if set(data.seed)-set.union(*partitions):
        raise ValueError("dataset contains unassigned seeds")
    if data.groupby("run_id").seed.nunique().gt(1).any():
        raise ValueError("run contains multiple seeds")
    return tuple(data[data.seed.isin(seeds)].copy() for seeds in partitions)


def train_models(data, output_dir, *, train_seeds=range(100,108), validation_seeds=range(200,203), test_seeds=range(300,305), max_iter=100):
    if not set(FEATURE_COLUMNS).issubset(data.columns):
        raise ValueError("missing feature columns")
    if not data.policy.eq("fixed").all():
        raise ValueError("first-response models require fixed-policy no-action labels")
    if np.isinf(data[list(FEATURE_COLUMNS)].to_numpy(dtype=float)).any():
        raise ValueError("infinite features")
    if 'data_source' in data and (data.data_source.isna().any() or data.data_source.eq('').any()):
        raise ValueError('missing training-data provenance')
    provenance=set(data.data_source) if 'data_source' in data else set()
    if len(provenance)>1:
        raise ValueError('mixed training-data provenance')
    data_source=next(iter(provenance)) if provenance else 'unverified_external_logs'
    steps=set(data.label_step_s) if 'label_step_s' in data else {5}
    if len(steps)!=1:
        raise ValueError('mixed label steps')
    label_step_s=validate_label_step(next(iter(steps)))
    train,val,_=split_by_seed(data,train_seeds,validation_seeds,test_seeds)
    output_dir=Path(output_dir); output_dir.mkdir(parents=True,exist_ok=True)
    report={"selection_split":"validation_only","data_source":data_source,"horizons":{}}
    prepared={};models={}
    for h in HORIZONS:
        target=f"target_{h}"
        fit=train.dropna(subset=[target]); score=val.dropna(subset=[target,"slowdown_now"])
        if 'forecast_eligible' in data:
            if not data.forecast_eligible.isin([True,False]).all():
                raise ValueError('forecast_eligible must be boolean')
            fit=fit[fit.forecast_eligible.eq(True)];score=score[score.forecast_eligible.eq(True)]
        if len(fit)<10 or not len(score):
            raise ValueError(f"not enough complete training/validation labels for {h}s")
        if not fit[target].between(0,1).all() or not score[target].between(0,1).all():
            raise ValueError("target outside slowdown range")
        prepared[h]=(fit,score)
    for h in HORIZONS:
        fit,score=prepared[h];target=f'target_{h}'
        # Internal fill values have explicit missingness indicators. Observation gaps
        # still remain null and cannot authorize control. Fit preprocessing on train only.
        estimator=make_pipeline(SimpleImputer(strategy='constant',fill_value=0,add_indicator=True,keep_empty_features=True),
                                HistGradientBoostingRegressor(max_iter=max_iter,max_leaf_nodes=15,min_samples_leaf=5,early_stopping=False,random_state=42))
        with threadpool_limits(limits=1):
            estimator.fit(fit[list(FEATURE_COLUMNS)].to_numpy(dtype=float),fit[target].to_numpy())
            predictions=np.clip(estimator.predict(score[list(FEATURE_COLUMNS)].to_numpy(dtype=float)),0,1)
        persistence=score.slowdown_now.to_numpy()
        trend=trend_prediction(persistence,score.slowdown_slope_60.to_numpy(),h,label_step_s=label_step_s)
        report["horizons"][str(h)]={"train_rows":len(fit),"validation_rows":len(score),
            "boosting_mae":float(mean_absolute_error(score[target],predictions)),
            "persistence_mae":float(mean_absolute_error(score[target],persistence)),
            "trend_mae":float(mean_absolute_error(score[target],trend))}
        models[h]=estimator
    model_hashes={}
    for h,estimator in models.items():
        path=output_dir/f'forecast-{h}.joblib'
        joblib.dump(estimator,path)
        model_hashes[str(h)]=sha256(path.read_bytes()).hexdigest()
    manifest={"artifact_version":2,"feature_version":FEATURE_VERSION,'label_step_s':label_step_s,"sklearn_version":sklearn.__version__,"feature_columns":list(FEATURE_COLUMNS),
              "horizons":list(HORIZONS),"train_seeds":sorted(set(train.seed)),"validation_seeds":sorted(set(val.seed)),
              "test_seeds":sorted(set(test_seeds)),"label_policy":"fixed_no_action", "training_data_sha256":sha256(data.to_csv(index=False).encode()).hexdigest(),
              "data_source":data_source,"model_sha256":model_hashes,
              "preprocessing":"training-fitted constant imputation with missingness indicators; online unknown coverage remains null"}
    (output_dir/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    (output_dir/"validation.json").write_text(json.dumps(report,indent=2,allow_nan=False),encoding="utf-8")
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset",required=True); p.add_argument("--output-dir",required=True)
    a=p.parse_args(argv)
    report=train_models(pd.read_csv(a.dataset),a.output_dir)
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()
