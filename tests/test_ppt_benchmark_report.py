import json
from pathlib import Path
from scripts.report_unified_benchmark import build_report

def test_report_preserves_faults_and_negative_results(tmp_path):
    # Reuse schema, not the artifact's performance numbers, to construct diagnostics.
    def manifest(policy, ident, journey, collision=0):
        return dict(run_id=ident,policy=policy,seed=42,network_sha256='n',demand_sha256='d',execution_sha256='e',settings={},scenario_requested='test',scenario_mutated=False,complete=True,integrity='complete' if not collision else 'faulted',mean_journey_s=journey,mean_travel_s=journey,mean_insertion_delay_s=0,final_counts=dict(scheduled=10,arrived=10,collisions=collision,teleports=0,co2_kg=1))
    attempts=[dict(seed=42,policy='fixed',manifest=manifest('fixed','b',100)),dict(seed=42,policy='pressure',manifest=manifest('pressure','r',110)),dict(seed=42,policy='bounded',manifest=manifest('bounded','f',80,2)),dict(seed=43,policy='fixed',error='timeout')]
    source=tmp_path/'batch.json';source.write_text(json.dumps(dict(runs=attempts)))
    report=build_report([source],tmp_path/'report')
    assert report['comparisons'][0]['differences']['journey_reduction_pct']==-10
    assert report['comparisons'][1]['available'] is False
    assert report['runs'][-1]['valid'] is False
    assert 'timeout' in (tmp_path/'report/report.md').read_text()


def test_integrity_string_cannot_override_collision_or_missing_measurement():
    from scripts.report_unified_benchmark import valid_cohort
    m=dict(complete=True,integrity='complete',mean_journey_s=20,final_counts=dict(scheduled=3,arrived=3,collisions=1,teleports=0))
    assert not valid_cohort(m)
    m['final_counts']['collisions']=0
    assert valid_cohort(m)
    m['mean_journey_s']=None
    assert not valid_cohort(m)


def test_results_summary_never_copies_full_live_recording():
    from fastapi.testclient import TestClient
    from backend.simulation.app import create_app
    class Engine:
        def start(self):pass
        def stop(self):pass
        def snapshot(self):return dict(ready=True,error=None,run_id='r',sim_time_s=10,vehicles=[],scenario='everyday',paused=False,result=dict(run_id='r',complete=False),action_log=[dict(kind='policy_selected')])
        def export(self):raise AssertionError('full recording must not be copied for a summary')
    with TestClient(create_app(Engine(),{'reader':{'role':'viewer','password':'fixture'}})) as client:
        assert client.get('/api/v2/results?summary=true').status_code==401
        token=client.post('/api/v2/auth/login',json={'username':'reader','password':'fixture'}).json()['token']
        result=client.get('/api/v2/results?summary=true',headers={'Authorization':'Bearer '+token})
        assert result.status_code==200
        assert result.json()['manifest']['run_id']=='r'
        assert result.json()['summary_only'] is True
        assert result.json()['frames']==[]
