"""Run each LIG scenario to its horizon; retain metrics and complete run artifacts."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.harness.engine import HarnessEngine, SCENARIOS, ROOT

results = []
for scenario in SCENARIOS:
    engine = HarnessEngine()
    try:
        # This script's main thread is the sole TraCI owner, just as the server's
        # simulation thread is during interactive use.
        engine._reset(scenario, 42)
        while engine._conn.simulation.getTime() < 1200:
            engine._step(publish=int(engine._conn.simulation.getTime()*4) % 4 == 3)
        engine._publish()
        engine._save()
        state = engine.snapshot()
        results.append(dict(scenario=scenario, run_id=engine.run_id,
                            sim_time_s=state['sim_time_s'],metrics=state['metrics'],
                            events=state['events'],complete=engine.export()['manifest']['complete']))
        print(json.dumps(results[-1]), flush=True)
    finally:
        if engine._conn: engine._conn.close()
(ROOT/'runs'/'lig-validation.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
