"""Read-only readiness check; never launches SUMO, a server or a download."""
import argparse
import importlib.util
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import sys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario',default='contracts/rain-demo.example.json')
    parser.add_argument('--output')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    dependencies={}
    for distribution in ['numpy','pandas','scikit-learn','matplotlib','jsonschema','pytest']:
        try:
            dependencies[distribution]=importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            dependencies[distribution]=None
    binary=shutil.which('sumo')
    if not binary and os.environ.get('SUMO_HOME'):
        candidate=Path(os.environ['SUMO_HOME'])/'bin'/'sumo.exe'
        binary=str(candidate) if candidate.is_file() else None
    scenario_path=Path(args.scenario)
    scenario_path=scenario_path if scenario_path.is_absolute() else root/scenario_path
    scenario=json.loads(scenario_path.read_text(encoding='utf-8'))
    assets={field:(root/scenario[field]).is_file() for field in ['sumocfg','network_file','demand_file','additional_file','id_registry_file']}
    report={'python':sys.version.split()[0],'dependencies':dependencies,'sumo_binary':binary,
            'traci_importable':importlib.util.find_spec('traci') is not None,'scenario_assets':assets,
            'ml_environment_ready':all(dependencies.values()),
            'real_sumo_runs_ready':bool(binary) and importlib.util.find_spec('traci') is not None and all(assets.values())}
    print(json.dumps(report,indent=2))
    if args.output:
        output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return 0 if report['real_sumo_runs_ready'] else 2


if __name__=='__main__':
    raise SystemExit(main())
