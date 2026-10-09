"""Repeat the fixed demo without UI; retain every integrity outcome."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.harness.demo_engine import DemoEngine, BASELINE_PATH


def run(repeats=3, save_baseline=False):
    results=[]
    for repeat in range(repeats):
        engine=DemoEngine()
        try:
            engine._reset()
            while not engine.snapshot()['ended']: engine._step()
            engine._save()
            record=engine.export(); manifest=record['manifest']; counts=manifest['final_counts']
            result=dict(repeat=repeat+1,run_id=engine.run_id,seed=engine.seed,scheduled=engine.scheduled,
                        arrived=engine.arrived,collisions=engine.collisions,teleports=engine.teleports,
                        unfinished=engine.scheduled-engine.arrived,complete=manifest['complete'],
                        sim_time_s=engine.snapshot()['sim_time_s'],mean_journey_s=manifest['mean_journey_s'],
                        scenario_sha256=manifest['scenario_sha256'],run_directory=str(engine.run_dir))
            results.append(result); print(json.dumps(result),flush=True)
            if save_baseline and repeat==0 and manifest['complete']:
                # Truth recording only, explicitly never a source of phone samples.
                record['label']='RECORDED BASELINE'; record['recording_policy']='fixed_no_guidance'
                BASELINE_PATH.write_text(json.dumps(record,separators=(',',':')),encoding='utf-8')
        finally:
            if engine._conn: engine._conn.close()
    output=Path('runs/demo-validation.json'); output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(results,indent=2),encoding='utf-8')
    passed=all(r['complete'] and r['collisions']==0 and r['teleports']==0 and r['unfinished']==0 for r in results)
    print('PASS: repeatable demo cohort' if passed else 'FAIL: incomplete or faulty demo',flush=True)
    return 0 if passed else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--repeats',type=int,default=3); parser.add_argument('--save-baseline',action='store_true')
    args=parser.parse_args(); raise SystemExit(run(args.repeats,args.save_baseline))
