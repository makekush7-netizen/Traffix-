"""Retain headless LIG diagnostics, including failed and unfinished cohorts."""
import argparse
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.harness.engine import HarnessEngine, SCENARIOS, ROOT

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenarios', nargs='+', choices=list(SCENARIOS), default=list(SCENARIOS))
    parser.add_argument('--seeds', nargs='+', type=int, default=[42])
    parser.add_argument('--profile', choices=['legacy', 'conservative'], default='legacy')
    parser.add_argument('--max-end-s', type=float)
    parser.add_argument('--demand-per-hour', type=float)
    parser.add_argument('--no-sublane', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    output = args.output or ROOT/'runs'/f'lig-validation.{args.profile}.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    results = []
    for scenario in args.scenarios:
        for seed in args.seeds:
            config = dict(profile=args.profile,
                          max_end_s=args.max_end_s or (1200 if args.profile == 'legacy' else 2400),
                          sublane=not args.no_sublane)
            if args.demand_per_hour is not None:
                config['demand_per_hour'] = args.demand_per_hour
            engine = HarnessEngine(run_config=config)
            started = time.monotonic()
            try:
                engine._reset(scenario, seed)
                while not engine._ended(engine._conn.simulation.getTime()):
                    engine._step(publish=round(engine._conn.simulation.getTime()*4) % 4 == 3)
                engine._publish()
                engine._save()
                state = engine.snapshot()
                results.append(dict(scenario=scenario, seed=seed, run_id=engine.run_id,
                                    sim_time_s=state['sim_time_s'], metrics=state['metrics'],
                                    events=state['events'], complete=engine.export()['manifest']['complete'],
                                    configuration=config, wall_time_s=round(time.monotonic()-started, 2)))
                print(json.dumps(results[-1]), flush=True)
                output.write_text(json.dumps(results, indent=2), encoding='utf-8')
            finally:
                if engine._conn:
                    engine._conn.close()


if __name__ == '__main__':
    main()
