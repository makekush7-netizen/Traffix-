from copy import deepcopy
from backend.simulation.results import compare_records


def record(run_id,policy,journey=10):
    return {'manifest':{'run_id':run_id,'policy':policy,'network_sha256':'n','demand_sha256':'d','execution_sha256':'e','seed':42,
            'settings':{},'scenario_requested':'everyday','scenario_mutated':False,'complete':True,'integrity':'complete',
            'mean_journey_s':journey,'mean_travel_s':8,'mean_insertion_delay_s':2,
            'final_counts':{'scheduled':2,'arrived':2,'collisions':0,'teleports':0,'co2_kg':1}},'frames':[]}


def test_saved_comparison_keeps_negative_results_and_rejects_mismatches():
    baseline=record('lig.111111111111','fixed'); response=record('lig.222222222222','pressure',12)
    reply=compare_records(response,baseline)
    assert reply['available'] and reply['differences']['journey_reduction_pct']==-20
    for change,reason in [({'execution_sha256':'old'},'configuration_or_execution_mismatch'),({'complete':False},'incomplete_or_faulted_cohort'),({'scenario_mutated':True},'scenario_was_edited')]:
        altered=deepcopy(response); altered['manifest'].update(change)
        assert compare_records(altered,baseline)['reason_code']==reason
    altered=deepcopy(response); del altered['manifest']['mean_journey_s']
    assert not compare_records(altered,baseline)['available']

def test_saved_real_sumo_paired_complete_results(tmp_path):
    from scripts.run_unified import prepare_environment
    from backend.simulation.engine import UnifiedEngine
    from backend.simulation.results import compare_records
    import json
    from pathlib import Path
    prepare_environment()
    records=[]
    for policy in ('fixed','bounded'):
        engine=UnifiedEngine(); engine.settings.update(demand_per_hour=500,duration_s=10,drain_s=1200)
        engine.start()
        try:
            actor={'id':'paired-test','role':'operator'}
            engine.command({'action':'lease','actor':actor,'lease_action':'acquire'}).result(5)
            engine.command({'action':'v2','actor':actor,'command':{'api_version':'2.0','command_id':'policy','run_id':engine.run_id,'expected_revision':0,'payload':{'action':'controller','policy':policy}}}).result(5)
            for _ in range(4840):
                if engine.snapshot()['ended']: break
                engine.command({'action':'step'}).result(5)
            record=engine.export(); records.append(record)
            assert record['manifest']['integrity']=='complete'
            assert record['manifest']['mean_journey_s']>0
            assert abs(record['manifest']['mean_journey_s']-record['manifest']['mean_travel_s']-record['manifest']['mean_insertion_delay_s'])<1e-8
            saved=json.loads((engine.run_dir/'recording.json').read_text())
            assert saved['manifest']['mean_journey_s']==record['manifest']['mean_journey_s']
        finally: engine.stop()
    comparison=compare_records(records[1],records[0])
    assert comparison['available']
    output=tmp_path/'unified-complete-pair.json'
    output.write_text(json.dumps(comparison,indent=2))

def test_compare_http_authentication_readonly_permissions_and_paths(tmp_path,monkeypatch):
    import json
    import backend.simulation.engine as module
    from fastapi.testclient import TestClient
    from backend.simulation.app import create_app
    monkeypatch.setattr(module,'ROOT',tmp_path)
    base='lig.111111111111'; response='lig.222222222222'
    for row in (record(base,'fixed'),record(response,'bounded',12)):
        directory=tmp_path/'runs'/row['manifest']['run_id']; directory.mkdir(parents=True)
        (directory/'recording.json').write_text(json.dumps(row))
    class Engine:
        def start(self): pass
        def stop(self): pass
        def snapshot(self): return {'ready':True,'error':None,'run_id':'run.1','sim_time_s':0,'vehicles':[],'scenario':'everyday','paused':True}
    with TestClient(create_app(Engine(),{'reader':{'role':'viewer','password':'fixture'}})) as client:
        path=f'/api/v2/runs/{response}/compare/{base}'
        assert client.get(path).status_code==401
        token=client.post('/api/v2/auth/login',json={'username':'reader','password':'fixture'}).json()['token']
        headers={'Authorization':'Bearer '+token}
        reply=client.get(path,headers=headers)
        assert reply.status_code==200 and reply.json()['differences']['journey_reduction_pct']==-20
        assert client.get('/api/v2/runs/secret/compare/'+base,headers=headers).status_code==422
        assert client.get('/api/v2/runs/lig.aaaaaaaaaaaa/compare/'+base,headers=headers).status_code==404
