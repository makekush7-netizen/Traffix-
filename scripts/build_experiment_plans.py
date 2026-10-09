"""Materialize the approved experiment lock. Planning only; no SUMO runs."""
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from eval.generate import main as generate


def main():
    root=Path(__file__).resolve().parents[1]/'artifacts'
    root.mkdir(exist_ok=True)
    scenarios=['scn.rain_ramp','scn.market_block','scn.procession']
    specifications=[
        ('training-plan',scenarios,range(100,108),['fixed'],['demand.reference','demand.high'],[.6],['mask.market_gap'],48),
        ('validation-plan',scenarios,range(200,203),['fixed'],['demand.reference','demand.high'],[.6],['mask.market_gap'],18),
        ('forecast-test-plan',scenarios,range(300,305),['fixed'],['demand.reference'],[.6],['mask.market_gap'],15),
        ('policy-plan',scenarios,range(300,305),['fixed','reactive','predictive'],['demand.reference'],[.6],['mask.market_gap'],45),
        ('sensor-ablation-plan',['scn.rain_ramp'],range(300,305),['predictive'],['demand.reference'],[.6],['mask.boundary_only','mask.market_gap'],10),
        ('compliance-plan',['scn.rain_ramp'],range(300,305),['reactive','predictive'],['demand.reference'],[0,.2,.6],['mask.market_gap'],30),
    ]
    counts={}
    for name,scenario,seeds,policies,demands,compliance,masks,count in specifications:
        path=root/f'{name}.json'
        generate(['plan','--scenarios',*scenario,'--seeds',*map(str,seeds),'--policies',*policies,
                  '--demand-ids',*demands,'--compliance-values',*map(str,compliance),'--sensor-masks',*masks,'--output',str(path)])
        jobs=json.loads(path.read_text(encoding='utf-8'))
        assert len(jobs)==count and len({job['run_id'] for job in jobs})==count
        counts[name]=count
    print(json.dumps({'planned_jobs':counts,'executed_SUMO_jobs':0,
                      'note':'Names are planned presets; resolve masks/demand files with the runner. Reuse identical core jobs in ablations/compliance.'},indent=2))


if __name__=='__main__':
    main()
