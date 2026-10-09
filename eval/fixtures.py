"""Artificial software fixtures. This does NOT run SUMO or simulate traffic physics."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from ml.observations import ObservationAggregator, ProbeSample


def write_fixture_logs(output_dir, *, seeds=tuple(range(100,108))+tuple(range(200,203))+tuple(range(300,305)), duration_s=900):
    output=Path(output_dir);output.mkdir(parents=True,exist_ok=True)
    observations=[];truth=[]
    for seed in seeds:
        rng=np.random.default_rng(seed)
        start=140+int(rng.integers(0,60));end=start+220+int(rng.integers(0,80))
        run=f'run.fixture.fixed.{seed}'
        sensor=ObservationAggregator({'edge.market':10})
        for t in range(0,duration_s+1,5):
            if t<start:
                value=.1
            elif t<end:
                value=min(.9,.1+(t-start)*.0035)
            else:
                value=max(.1,.9-(t-end)*.008)
            if not (seed%2==0 and 300<=t<=350):
                for v in ['veh.fixture.a','veh.fixture.b']:
                    noisy=float(np.clip(value+rng.normal(0,.025),0,1))
                    sensor.add_probe(ProbeSample(v,'edge.market',t,10*(1-noisy),source='emulated_probe'))
            obs=sensor.snapshot('edge.market',t)
            observations.append({**obs.to_payload(),'sources':','.join(obs.sources),'fresh_probes':obs.fresh_probes,
                                 'run_id':run,'seed':seed,'policy':'fixed','data_source':'fixture','sim_time_s':t,
                                 'serving_green':(t%60)<30,'phase_age_s':t%30})
            truth.append(dict(run_id=run,seed=seed,policy='fixed',data_source='fixture',edge_id='edge.market',sim_time_s=t,
                              slowdown_true=value,jam_length_m=100 if value>=.7 else 0,
                              serving_green=(t%60)<30,phase_age_s=t%30,jam_label=value>=.7))
    pd.DataFrame(observations).to_csv(output/'observations.csv',index=False)
    pd.DataFrame(truth).to_csv(output/'truth.csv',index=False)
    (output/'FIXTURE-ONLY.txt').write_text('Artificial time-series fixtures, not SUMO, phones, India traffic measurements or performance proof. Never use these numbers as traffic results.\n',encoding='utf-8')
    (output/'fixture-manifest.json').write_text(json.dumps({'data_source':'fixture','seeds':list(seeds),'duration_s':duration_s,'step_s':5},indent=2),encoding='utf-8')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-dir',required=True);p.add_argument('--duration-s',type=int,default=900)
    a=p.parse_args(argv);write_fixture_logs(a.output_dir,duration_s=a.duration_s)


if __name__=='__main__':
    main()
