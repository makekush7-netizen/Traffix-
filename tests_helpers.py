"""Small deterministic unit-test dataset; never a traffic-performance result."""
import pandas as pd
from ml.features import FEATURE_COLUMNS


def trained_dataset():
    rows=[]
    for seed in [100,200,300]:
        for i in range(40):
            row={name:0.0 for name in FEATURE_COLUMNS}
            row.update(run_id=f'run.{seed}',seed=seed,policy='fixed',edge_id='edge.market',sim_time_s=i*5,
                       slowdown_now=i/100,history_span_s=60,fresh_fraction_60=1,distinct_probes_60s=2,
                       forecast_eligible=True,data_source='fixture',target_120=min(1,i/100+.2),target_180=min(1,i/100+.3),target_300=min(1,i/100+.5))
            rows.append(row)
    return pd.DataFrame(rows)
