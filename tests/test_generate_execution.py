import json
import sys
import pytest
from eval.generate import main


def test_success_exit_without_exports_is_not_a_successful_run(tmp_path):
    plan=tmp_path/'plan.json'
    plan.write_text(json.dumps([{'run_id':'run.empty'}]))
    with pytest.raises(RuntimeError,match='export'):
        main(['execute','--plan',str(plan),'--output-dir',str(tmp_path/'runs'),'--runner',sys.executable,'-c','print("no exports")'])


def test_run_id_cannot_escape_output_folder(tmp_path):
    plan=tmp_path/'plan.json'
    plan.write_text(json.dumps([{'run_id':'../outside'}]))
    with pytest.raises(ValueError,match='run_id'):
        main(['execute','--plan',str(plan),'--output-dir',str(tmp_path/'runs'),'--runner',sys.executable,'-c','print("bad")'])


def test_plan_can_generate_fixed_only_training_and_sensor_ablations(tmp_path):
    path=tmp_path/'plan.json'
    main(['plan','--scenarios','scn.rain_ramp','--seeds','100','200','--policies','fixed',
          '--compliance-values','0','0.6','--sensor-masks','mask.none','mask.phones','--output',str(path)])
    jobs=json.loads(path.read_text())
    assert len(jobs)==8 and {job['policy'] for job in jobs}=={'fixed'}
