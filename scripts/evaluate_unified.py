"""Small paired host experiment; saves faults and incomplete runs honestly."""
import argparse
import json
import time
import uuid
from pathlib import Path
from scripts.run_unified import prepare_environment


def run(seed, policy, rate, duration, drain):
    from backend.simulation.engine import UnifiedEngine
    engine = UnifiedEngine()
    actor = {'id': 'batch-evaluator', 'role': 'operator'}
    started = time.perf_counter()
    engine.start()
    try:
        def command(payload):
            engine.command({'action': 'lease', 'actor': actor, 'lease_action': 'acquire'}).result(15)
            state = engine.state()
            return engine.command({'action': 'v2', 'actor': actor, 'command': {
                'api_version': '2.0', 'command_id': str(uuid.uuid4()),
                'run_id': state['run']['run_id'], 'expected_revision': state['revision'],
                'payload': payload}}).result(30)
        command({'action': 'reset', 'seed': seed, 'settings': {
            'mode': 'experiment', 'demand_per_hour': rate,
            'duration_s': duration, 'drain_s': drain}})
        command({'action': 'controller', 'policy': policy})
        command({'action': 'rate', 'value': 8})
        command({'action': 'resume'})
        deadline = time.monotonic() + 180
        while not engine.snapshot().get('ended'):
            if engine.failure:
                raise RuntimeError(str(engine.failure))
            if time.monotonic() > deadline:
                raise TimeoutError('host experiment wall deadline')
            time.sleep(.05)
        record = engine.export()
        return {'seed': seed, 'policy': policy, 'wall_s': time.perf_counter()-started,
                'manifest': record['manifest'], 'final': engine.snapshot(),
                'events': record['events']}
    finally:
        engine.stop()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--seeds', type=int, nargs='+', default=[42, 43])
    p.add_argument('--policies', nargs='+', default=['fixed', 'bounded', 'pressure'])
    p.add_argument('--rate', type=float, default=500)
    p.add_argument('--duration', type=float, default=30)
    p.add_argument('--drain', type=float, default=600)
    p.add_argument('--output', default='runs/unified-paired-smoke.json')
    a = p.parse_args()
    prepare_environment()
    records = []
    output = Path(a.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    for seed in a.seeds:
        for policy in a.policies:
            try:
                record = run(seed, policy, a.rate, a.duration, a.drain)
            except Exception as exc:
                record = {'seed': seed, 'policy': policy, 'error': str(exc)}
            records.append(record)
            output.write_text(json.dumps({'label': 'synthetic short-cohort smoke; not calibrated improvement evidence',
                                         'runs': records}, indent=2), encoding='utf-8')
            print(seed, policy, record.get('manifest', {}).get('integrity', record.get('error')), flush=True)
    return 1 if any(r.get('error') for r in records) else 0

if __name__ == '__main__':
    raise SystemExit(main())

