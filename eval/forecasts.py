"""Frozen held-out evaluation. These are forecast scores, never journey gains."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error
from threadpoolctl import threadpool_limits
from ml.features import FEATURE_COLUMNS
from ml.forecast import ForecastService, HORIZONS, trend_prediction


def confusion(y_true, y_pred):
    truth=np.asarray(y_true,dtype=bool); pred=np.asarray(y_pred,dtype=bool)
    tp=int(np.sum(truth & pred)); fp=int(np.sum(~truth & pred)); fn=int(np.sum(truth & ~pred)); tn=int(np.sum(~truth & ~pred))
    return {'true_positive':tp,'false_positive':fp,'false_negative':fn,'true_negative':tn,
            'precision':tp/(tp+fp) if tp+fp else None,'recall':tp/(tp+fn) if tp+fn else None}


def evaluate_forecasts(data, model_dir, *, danger=0.7):
    directory=Path(model_dir)
    manifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    test_seeds=set(manifest['test_seeds'])
    if test_seeds & (set(manifest['train_seeds']) | set(manifest['validation_seeds'])):
        raise ValueError('test seeds overlap training or validation artifacts')
    test=data[data.seed.isin(test_seeds)].copy()
    if test.empty:
        raise ValueError('no declared test seeds available')
    if not test.policy.eq('fixed').all():
        raise ValueError('forecast test requires no-action labels')
    if 'data_source' not in test or test.data_source.isna().any() or not test.data_source.eq(manifest['data_source']).all():
        raise ValueError('held-out data provenance differs from model provenance')
    if 'label_step_s' in test and not test.label_step_s.eq(manifest['label_step_s']).all():
        raise ValueError('held-out label step mismatch')
    service=ForecastService.from_directory(directory)
    report={'split':'test_only','test_seeds':sorted(set(test.seed)),
            'missing_test_seeds':sorted(test_seeds-set(test.seed)),'data_source':manifest['data_source'],
            'danger_threshold_starting_value':danger,'horizons':{}}
    if 'forecast_eligible' not in test:
        raise ValueError('missing forecast_eligible coverage gate; rebuild dataset')
    if not test.forecast_eligible.isin([True,False]).all():
        raise ValueError('forecast_eligible must be boolean')
    for h in HORIZONS:
        labeled=test.dropna(subset=[f'target_{h}','slowdown_now'])
        score=labeled[labeled.forecast_eligible.eq(True)]
        methods={}
        if not score.empty:
            y=score[f'target_{h}'].to_numpy()
            if not np.isfinite(y).all() or ((y<0)|(y>1)).any():
                raise ValueError('invalid held-out target')
            persistence=score.slowdown_now.to_numpy()
            trend=trend_prediction(persistence,score.slowdown_slope_60.to_numpy(),h,label_step_s=manifest['label_step_s'])
            with threadpool_limits(limits=1):
                boosting=np.clip(service.models[h].predict(score[list(FEATURE_COLUMNS)].to_numpy(dtype=float)),0,1)
            for method,pred in [('persistence',persistence),('trend',trend),('boosting',boosting)]:
                seed_mae={str(seed):float(mean_absolute_error(y[score.seed.to_numpy()==seed],pred[score.seed.to_numpy()==seed])) for seed in sorted(set(score.seed))}
                methods[method]={'mae':float(mean_absolute_error(y,pred)), 'per_seed_mae':seed_mae,
                                 'macro_seed_mae':float(np.mean(list(seed_mae.values()))),**confusion(y>=danger,pred>=danger)}
        report['horizons'][str(h)]={'rows_total':len(test),'labeled_rows':len(labeled),'eligible_rows':len(score),
                                  'eligible_fraction':len(score)/len(test),'methods':methods}
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset',required=True);p.add_argument('--models',required=True);p.add_argument('--output',required=True)
    a=p.parse_args(argv)
    report=evaluate_forecasts(pd.read_csv(a.dataset),a.models)
    output=Path(a.output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
