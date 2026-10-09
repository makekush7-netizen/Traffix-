"""Read-only truth telemetry for simulation QA, never an operational observation feed."""
import csv
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_nandani import prepare_environment


def main():
    prepare_environment()
    import traci
    from sim import run_incident_headless

    telemetry = []
    stop_requests = []
    stopped = []
    vehicle_types = {}
    original_step, original_stop, original_start = traci.simulationStep, traci.vehicle.setStop, traci.start

    def start(*args, **kwargs):
        result = original_start(*args, **kwargs)
        # Querying a distribution ID can sample it and consume simulation RNG.
        # Inspect only concrete vTypes, keeping this telemetry observational.
        distributions = {node.get('id') for path in (ROOT / 'sim/demand').glob('*.xml')
                         for node in ET.parse(path).getroot().iter('vTypeDistribution')}
        for type_id in traci.vehicletype.getIDList():
            if type_id in distributions:
                continue
            vehicle_types[type_id] = dict(vclass=traci.vehicletype.getVehicleClass(type_id),
                                         length_m=traci.vehicletype.getLength(type_id),
                                         width_m=traci.vehicletype.getWidth(type_id))
        return result

    def step(*args, **kwargs):
        result = original_step(*args, **kwargs)
        time = traci.simulation.getTime()
        if time % 5 == 0:
            row = dict(sim_time_s=time, downstream_state=traci.trafficlight.getRedYellowGreenState('J4'))
            for edge in ('main1', 'main2'):
                row[edge + '_vehicles'] = traci.edge.getLastStepVehicleNumber(edge)
                row[edge + '_halted'] = traci.edge.getLastStepHaltingNumber(edge)
                row[edge + '_speed_mps'] = traci.edge.getLastStepMeanSpeed(edge)
            ids = set(traci.vehicle.getIDList())
            for role in ('rider', 'auto', 'delivery'):
                vehicle = 'veh.role.' + role
                row[role + '_edge'] = traci.vehicle.getRoadID(vehicle) if vehicle in ids else ''
            if 'veh.role.delivery' in ids and traci.vehicle.isStopped('veh.role.delivery'):
                stopped.append(time)
            telemetry.append(row)
        return result

    def stop(vehicle, *args, **kwargs):
        stop_requests.append(dict(sim_time_s=traci.simulation.getTime(), vehicle=vehicle,
                                  current_edge=traci.vehicle.getRoadID(vehicle), arguments=list(args), options=kwargs))
        return original_stop(vehicle, *args, **kwargs)

    traci.simulationStep, traci.vehicle.setStop, traci.start = step, stop, start
    try:
        result = run_incident_headless.run(42, 2400)
    finally:
        traci.simulationStep, traci.vehicle.setStop, traci.start = original_step, original_stop, original_start
    output = ROOT / 'runs' / result['run_id'] / 'output'
    with (output / 'qa_truth_telemetry.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(telemetry[0]))
        writer.writeheader()
        writer.writerows(telemetry)
    summary = dict(source='SIMULATION TRUTH — QA ONLY', stop_requests=stop_requests, vehicle_types=vehicle_types,
                   first_delivery_stopped_sample_s=min(stopped) if stopped else None,
                   last_delivery_stopped_sample_s=max(stopped) if stopped else None,
                   max_market_halted=max(r['main1_halted'] + r['main2_halted'] for r in telemetry),
                   max_market_halted_during_downstream_market_green=max(
                       (r['main1_halted'] + r['main2_halted'] for r in telemetry if r['downstream_state'] == 'rrGGG'), default=0),
                   roles_present_at_rain_start={role: next(r for r in telemetry if r['sim_time_s'] == 300)[role + '_edge']
                                                for role in ('rider', 'auto', 'delivery')})
    (output / 'qa_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))
    print('Telemetry:', output)


if __name__ == '__main__':
    main()
