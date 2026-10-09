import json
from pathlib import Path
import pytest
from eval.integrity import merge_integrity

@pytest.mark.parametrize('evidence',[{'teleported':1},{'teleported':0,'final_counts':{'teleports':2}}])
def test_positive_or_conflicting_teleport_evidence_cannot_be_valid(evidence):
    result=merge_integrity(dict(data_source='sumo',collisions=0,**evidence),dict(valid=True,complete=True))
    assert not result['valid'] and not result['simulation_integrity_valid']
    assert 'teleport_evidence' in result['invalid_reasons']

def test_model_selection_identity_mismatch_fails_before_sumo(tmp_path):
    from ml.artifacts import execution_artifacts
    (tmp_path/'manifest.json').write_text(json.dumps({'data_source':'sumo'}))
    with pytest.raises(ValueError,match='identity'):
        execution_artifacts(tmp_path,{'model_manifest_sha256':'another-model'})

def test_resume_rejects_changed_execution_identity(tmp_path,monkeypatch):
    from eval.lig_pipeline import execute_jobs
    job=dict(run_id='run.lig.resume',scenario_id='lig.everyday',seed=100,policy='fixed',compliance=.6,
             sensor_mask_id='mask.lig.probes',demand_id='demand.lig.ordinary',data_source='sumo')
    folder=tmp_path/job['run_id'];folder.mkdir()
    (folder/'manifest.json').write_text(json.dumps({**job,'execution_sha256':'old-controller','valid':True,
                                                   'training_eligible':True,'scheduled':1,'arrived':1,'collisions':0,'wall_time_s':1}))
    for name in ['observations.csv','truth.csv','trips.csv','lifecycle.csv','events.json','sumo.log']:
        (folder/name).write_text('evidence')
    with pytest.raises(RuntimeError,match='runner failures'):
        execute_jobs([job],tmp_path,workers=1)
    assert 'identity' in json.loads((tmp_path/'batch-status.json').read_text())['failures'][0]['error']

def test_missing_policy_action_evidence_does_not_erase_missing_run_report(tmp_path,monkeypatch):
    import eval.lig_analysis as analysis
    monkeypatch.setattr(analysis,'collect_results',lambda path:{'results':[],'errors':[]})
    target=tmp_path/'report.json'
    report=analysis.policy_report(tmp_path,tmp_path,[300],target)
    assert target.exists() and report['invalid_runs']
    assert report['collection_errors']

def test_different_response_execution_identity_cannot_be_paired():
    from eval.compare import compare_results
    from tests.test_compare import result
    with pytest.raises(ValueError,match='execution'):
        compare_results([result('fixed',100),dict(result('reactive',90),execution_sha256='a'),
                         dict(result('predictive',80),execution_sha256='b')])
