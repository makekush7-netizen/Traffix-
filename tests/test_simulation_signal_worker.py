from types import SimpleNamespace
from backend.simulation.engine import UnifiedEngine


class Lights:
    def __init__(self):
        self.phase=0; self.state='Gr'; self.spent=20; self.remaining=.5; self.calls=[]
        self.phases=[SimpleNamespace(state='Gr',duration=30),SimpleNamespace(state='yr',duration=3),SimpleNamespace(state='rG',duration=30),SimpleNamespace(state='ry',duration=3)]
    def getIDList(self): return ['tls']
    def getRedYellowGreenState(self,t): return self.state
    def getControlledLinks(self,t): return [(('in0','out0',''),),(('in1','out1',''),)]
    def getPhase(self,t): return self.phase
    def getAllProgramLogics(self,t): return [SimpleNamespace(programID='0',phases=self.phases)]
    def getProgram(self,t): return '0'
    def getSpentDuration(self,t): return self.spent
    def getNextSwitch(self,t): return self.remaining
    def setPhase(self,t,p): self.phase=p; self.state=self.phases[p].state; self.calls.append(('phase',p))
    def setPhaseDuration(self,t,d): self.calls.append(('duration',d))
    def setRedYellowGreenState(self,t,state): self.state=state; self.calls.append(('state',state))
    def setProgram(self,t,p): self.calls.append(('program',p))


class Lanes:
    def getLastStepHaltingNumber(self,l): return 1 if l=='in0' else 10
    def getLength(self,l): return 150
    def getLastStepVehicleNumber(self,l): return 0
    def getEdgeID(self,l): return l
    def getLastStepVehicleIDs(self,l): return ()


def host(policy='pressure'):
    obj=UnifiedEngine.__new__(UnifiedEngine)
    obj.clock=0
    obj._conn=SimpleNamespace(trafficlight=Lights(),lane=Lanes(),simulation=SimpleNamespace(getTime=lambda:obj.clock))
    obj.policy=policy; obj.outage_edges=set(); obj._phase_extension={}; obj._events=[]
    return obj


def test_pressure_selected_target_requires_yellow_then_allred():
    h=host(); h._control_signals()
    assert h._conn.trafficlight.calls[0]==('phase',1)
    assert not any(c==('phase',2) for c in h._conn.trafficlight.calls)
    h.clock=3; h._control_signals()
    assert ('state','rr') in h._conn.trafficlight.calls
    assert not any(c==('phase',2) for c in h._conn.trafficlight.calls)
    h.clock=4; h._control_signals()
    assert h._conn.trafficlight.calls[-2:]==[('program','0'),('phase',2)]
    assert h._events[-1]['kind']=='signal_transition_completed'


def test_pressure_stale_target_cancels_after_clearance():
    h=host(); h._control_signals(); h.clock=3; h._control_signals()
    h.outage_edges={'in1'}; h.clock=4; h._control_signals()
    assert ('phase',2) not in h._conn.trafficlight.calls
    assert h._events[-1]['reason']=='target_no_longer_safe'


def test_actuated_gap_does_not_alias_queue_rule():
    h=host('actuated'); h._control_signals()
    h.clock=3; h._control_signals()
    assert not any(kind=='duration' for kind,*_ in h._conn.trafficlight.calls)
