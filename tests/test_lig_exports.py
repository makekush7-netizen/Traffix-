import json
import xml.etree.ElementTree as ET
import pandas as pd
import pytest

def test_registry_resolves_actual_network_and_keeps_frozen_references():
    from eval.lig_registry import load_registry
    registry=load_registry()
    assert registry['focus_edge']=='edge.lig.approach.0'
    edges=registry['edges']
    assert edges[registry['focus_edge']]['sumo_id']=='191621641#11'
    assert edges[registry['focus_edge']]['reference_speed_mps']==13.9
    assert all('#' not in logical for logical in edges)
    assert all(value['length_m']>0 for value in edges.values())
    assert registry['tls_sumo_id'].startswith('cluster_')
    assert edges[registry['focus_edge']]['signal_indices']

def test_job_resolution_rejects_old_corridor_and_unsupported_inputs():
    from eval.lig_runner import resolve_job
    job=dict(run_id='run.lig.test',scenario_id='lig.rain',seed=100,policy='fixed',
             compliance=.6,sensor_mask_id='mask.lig.probes',demand_id='demand.lig.ordinary',data_source='sumo')
    cfg=resolve_job(job)
    assert cfg['incident_ramp_s']==120 and cfg['sublane'] is False
    with pytest.raises(ValueError,match='scenario'):
        resolve_job({**job,'scenario_id':'rain_ramp'})
    with pytest.raises(ValueError,match='mask'):
        resolve_job({**job,'sensor_mask_id':'mask.market_gap'})
    with pytest.raises(ValueError,match='source'):
        resolve_job({**job,'data_source':'fixture'})

def test_zero_uplink_and_explicit_probe_assignment():
    from eval.lig_registry import probe_assignment
    vehicles=['car.1','motorcycle.2','bus.3']
    assert probe_assignment(vehicles,42,0)==[]
    assert probe_assignment(vehicles,42,1)==sorted(vehicles)
    assert probe_assignment(vehicles,42,.6)==probe_assignment(reversed(vehicles),42,.6)

def test_collision_logs_rejected_for_training_even_if_arrivals_complete(tmp_path):
    from eval.merge import merge_run_logs
    run=tmp_path/'run';run.mkdir()
    manifest=dict(run_id='run',seed=100,policy='fixed',data_source='sumo',scenario_id='lig.rain',
                  collisions=1,teleported=0,complete=True)
    (run/'manifest.json').write_text(json.dumps(manifest))
    pd.DataFrame([dict(edge_id='e',sim_time_s=5,coverage='fresh',slowdown=.2)]).to_csv(run/'observations.csv',index=False)
    pd.DataFrame([dict(edge_id='e',sim_time_s=5,slowdown_true=.2)]).to_csv(run/'truth.csv',index=False)
    with pytest.raises(ValueError,match='integrity'):
        merge_run_logs(tmp_path)
