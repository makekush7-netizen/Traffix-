from backend.simulation.coordination import Coordinator, Conflict
import pytest


def envelope(action='pause', command_id='c1', revision=0):
    return {'api_version':'2.0','command_id':command_id,'run_id':'run.1','expected_revision':revision,'payload':{'action':action}}


def test_serialized_revision_lease_idempotency_and_role():
    clock=[100.0]
    c=Coordinator(clock=lambda:clock[0])
    operator={'id':'alice','role':'operator'}
    viewer={'id':'bob','role':'viewer'}
    with pytest.raises(Conflict,match='operator_required'): c.acquire(viewer)
    c.acquire(operator)
    calls=[]
    execute=lambda payload: calls.append(payload) or {'sim_time_s':2}
    first=c.execute(operator,envelope(),'run.1',execute)
    assert first['revision']==1
    assert c.execute(operator,envelope(),'run.1',execute)==first
    assert len(calls)==1
    with pytest.raises(Conflict,match='revision_conflict'): c.execute(operator,envelope(command_id='c2'),'run.1',execute)
    with pytest.raises(Conflict,match='command_id_reused'): c.execute(operator,envelope('resume'),'run.1',execute)
    clock[0]+=31
    with pytest.raises(Conflict,match='lease_required'): c.execute(operator,envelope(command_id='c3',revision=1),'run.1',execute)


def test_wrong_run_and_failed_action_do_not_advance_revision():
    c=Coordinator(); actor={'id':'alice','role':'operator'}; c.acquire(actor)
    with pytest.raises(Conflict,match='wrong_run'): c.execute(actor,envelope(),'run.2',lambda p:None)
    def fail(p): raise ValueError('invalid')
    with pytest.raises(ValueError): c.execute(actor,envelope(),'run.1',fail)
    assert c.revision==0
