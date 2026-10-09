"""Signal-aware persistence detector; thresholds are unvalidated starting values."""
from dataclasses import dataclass
from ml.observations import finite


@dataclass(frozen=True)
class DetectionState:
    edge_id: str
    active: bool
    usable_for_control: bool
    evidence_s: float
    reason: str


class DetectionEngine:
    def __init__(self, danger=0.7, clear=0.3, persistence_s=30, recovery_s=60, min_probes=2, max_gap_s=15, green_evidence_s=10):
        for name,value in [('danger',danger),('clear',clear),('persistence',persistence_s),('recovery',recovery_s),('gap',max_gap_s),('green evidence',green_evidence_s)]:
            finite(value,name)
        if not 0 <= clear < danger <= 1 or min(persistence_s, recovery_s, max_gap_s, green_evidence_s) <= 0 or not isinstance(min_probes,int) or isinstance(min_probes,bool) or min_probes<1:
            raise ValueError("invalid detector settings")
        self.danger, self.clear = danger, clear
        self.persistence_s, self.recovery_s = persistence_s, recovery_s
        self.min_probes, self.max_gap_s = min_probes, max_gap_s
        self.green_evidence_s=green_evidence_s
        self.states = {}

    def update(self, observation, *, serving_green, phase_age_s):
        o = observation
        finite(phase_age_s,'phase age')
        if type(serving_green) is not bool:
            raise ValueError('serving_green must be boolean')
        s = self.states.setdefault(o.edge_id, {"last": None, "high": None, "low": None, "green_high":None, "phase_age":None, "active": False})
        if s["last"] is not None and o.sim_time_s <= s["last"]:
            raise ValueError("observation clock went backwards; reset per run")
        if s["last"] is not None and o.sim_time_s-s["last"] > self.max_gap_s:
            s["high"] = s["low"] = s['green_high'] = None
        if not serving_green or phase_age_s<5 or (s['phase_age'] is not None and phase_age_s<s['phase_age']):
            s['green_high']=None
        s['phase_age']=phase_age_s if serving_green else None
        s["last"] = o.sim_time_s
        usable = o.coverage == "fresh" and o.slowdown is not None and ("fixed" in o.sources or o.fresh_probes >= self.min_probes)
        if not usable:
            s["high"] = s["low"] = s['green_high'] = None
            return DetectionState(o.edge_id, s["active"], False, 0, "insufficient_evidence")
        if o.slowdown >= self.danger:
            s["low"] = None
            if s["high"] is None:
                s["high"] = o.sim_time_s
            evidence = o.sim_time_s-s["high"]
            if serving_green and phase_age_s>=5 and s['green_high'] is None:
                s['green_high']=o.sim_time_s
            served=s['green_high'] is not None and o.sim_time_s-s['green_high']>=self.green_evidence_s
            if evidence >= self.persistence_s and served:
                s["active"] = True
            reason = "persistent_congestion" if s["active"] else ("waiting_for_serving_phase" if not serving_green else "collecting_evidence")
        else:
            evidence = 0
            s["high"] = None
            s['green_high']=None
            if o.slowdown < self.clear:
                if s["low"] is None:
                    s["low"] = o.sim_time_s
                if o.sim_time_s-s["low"] >= self.recovery_s:
                    s["active"] = False
            else:
                s["low"] = None
            reason = "recovering" if s["active"] else "normal"
        return DetectionState(o.edge_id, s["active"], True, evidence, reason)
