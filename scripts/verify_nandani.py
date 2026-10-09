"""Audit the pushed simulation without editing Nandani's source files.

Run with .venv/Scripts/python.exe scripts/verify_nandani.py.
Evidence is saved under ignored runs/, including unfiltered SUMO stderr.
"""
import collections
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def prepare_environment():
    import sumo
    home = Path(sumo.SUMO_HOME)
    os.environ['SUMO_HOME'] = str(home)
    os.environ['PATH'] = str(Path(sys.executable).parent) + os.pathsep + str(home / 'bin') + os.pathsep + os.environ['PATH']
    return home


def static_audit():
    from jsonschema import Draft202012Validator
    scenario = json.loads((ROOT / 'sim/scenarios/rain_ramp.json').read_text(encoding='utf-8'))
    schema = json.loads((ROOT / 'contracts/scenario.schema.json').read_text(encoding='utf-8'))
    registry = json.loads((ROOT / 'sim/net/id-registry.json').read_text(encoding='utf-8'))
    net = ET.parse(ROOT / 'sim/net/bazaar.net.xml').getroot()
    config = ET.parse(ROOT / 'sim/net/bazaar.sumocfg').getroot()
    demand_paths = [ROOT / 'sim/net' / name for name in config.find('input/route-files').get('value').split(',')]
    counts = collections.Counter(v.get('id') for path in demand_paths for v in ET.parse(path).getroot().iter('vehicle'))
    errors = list(Draft202012Validator(schema).iter_errors(scenario))
    issues = []
    duplicates = {key: count for key, count in counts.items() if count > 1}
    if duplicates:
        issues.append(dict(kind='duplicate_role_vehicles', details=duplicates))
    invalid_inheritance = [dict(file=str(path.relative_to(ROOT)), vtype=node.get('id'), ignored_type=node.get('type'))
                           for path in demand_paths for node in ET.parse(path).getroot().iter('vType')
                           if node.get('type') is not None]
    if invalid_inheritance:
        issues.append(dict(kind='vtype_uses_type_instead_of_refId', details=invalid_inheritance))
    if errors:
        issues.append(dict(kind='scenario_contract_mismatch', count=len(errors),
                           details=[dict(path=e.json_path, message=e.message) for e in errors]))
    if net.get('lefthand') not in ('true', '1'):
        issues.append(dict(kind='left_hand_traffic_not_enabled', details=net.attrib))
    max_green = scenario['controller_settings']['max_green_s']
    oversized = [dict(signal=tl.get('id'), phase=i, duration_s=float(phase.get('duration')))
                 for tl in net.findall('tlLogic') for i, phase in enumerate(tl.findall('phase'))
                 if ('G' in phase.get('state') or 'g' in phase.get('state')) and float(phase.get('duration')) > max_green]
    if oversized:
        issues.append(dict(kind='fixed_green_exceeds_proposed_controller_bound', details=oversized))
    connections = {(c.get('from'), c.get('to')) for c in net.findall('connection')}
    for name, route in registry['routes'].items():
        if name.startswith('_'):
            continue
        for pair in zip(route['edges'], route['edges'][1:]):
            if pair not in connections:
                issues.append(dict(kind='broken_route_connection', route=name, edges=pair))
    detectors = ET.parse(ROOT / 'sim/net/detectors.add.xml').getroot()
    lane_ids = {lane.get('id') for edge in net.findall('edge') for lane in edge.findall('lane')}
    for det in detectors:
        if det.get('lane') not in lane_ids:
            issues.append(dict(kind='unresolved_detector_lane', detector=det.get('id')))
    return issues


def execute(command, output, name, timeout=180):
    try:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=timeout)
        stdout, stderr, code = result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired as exc:
        stdout, stderr, code = str(exc.stdout or ''), str(exc.stderr or ''), -1
    (output / f'{name}.stdout.txt').write_text(stdout, encoding='utf-8')
    (output / f'{name}.stderr.txt').write_text(stderr, encoding='utf-8')
    print(f'{name}: exit {code}')
    if code:
        print((stdout + stderr)[-2500:])
    return dict(name=name, exit_code=code, stdout=f'{name}.stdout.txt', stderr=f'{name}.stderr.txt')


def main():
    prepare_environment()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    output = ROOT / 'runs' / f'verify.nandani.{stamp}'
    output.mkdir(parents=True)
    report = dict(source='SIMULATION HANDOFF AUDIT — NOT TRAFFIC IMPROVEMENT RESULTS',
                  commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  issues=static_audit(), checks=[])
    report['checks'].append(execute(['sumo', '--version'], output, 'sumo_version'))
    report['checks'].append(execute([sys.executable, 'scripts/check_env.py'], output, 'environment'))
    report['checks'].append(execute([sys.executable, '-m', 'pytest', '-q'], output, 'pytest'))
    # Runner output paths and detector files remain exactly as supplied by Nandani.
    report['checks'].append(execute([sys.executable, 'sim/run_headless.py', '--seed', '42', '--end', '2400'],
                                    output, 'no_incident_2400s'))
    report['checks'].append(execute([sys.executable, 'sim/run_incident_headless.py', '--seed', '42', '--end', '2400'],
                                    output, 'incident_2400s'))
    report['input_sha256'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in (ROOT / 'sim').rglob('*') if p.is_file() and p.suffix in ('.xml', '.json', '.py', '.sumocfg')
                             and 'output' not in p.parts and '__pycache__' not in p.parts}
    (output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('Evidence:', output)
    print('Static issues:', ', '.join(i['kind'] for i in report['issues']))
    return 1 if report['issues'] or any(c['exit_code'] for c in report['checks']) else 0


if __name__ == '__main__':
    sys.exit(main())
