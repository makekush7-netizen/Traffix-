"""Predictive first-response eligibility only. Controller still owns all actions."""
from dataclasses import dataclass
from ml.observations import finite


@dataclass(frozen=True)
class TriggerDecision:
    eligible: bool
    evidence_s: float
    reason: str


class FirstResponseTrigger:
    def __init__(self, *, danger=.7, min_current_slowdown=.3, persistence_s=20, max_gap_s=15, green_evidence_s=10):
        for name,value in [('danger',danger),('minimum',min_current_slowdown),('persistence',persistence_s),('gap',max_gap_s),('green evidence',green_evidence_s)]:
            finite(value,name)
        if not 0<=min_current_slowdown<danger<=1 or min(persistence_s,max_gap_s,green_evidence_s)<=0:
            raise ValueError('invalid first-response settings')
        self.danger,self.minimum,self.persistence_s,self.max_gap_s=danger,min_current_slowdown,persistence_s,max_gap_s
        self.green_evidence_s=green_evidence_s
        self.states={}

    def update(self, observation, forecast, *, serving_green, phase_age_s, intervention_active=False):
        o=observation;finite(phase_age_s,'phase age')
        if type(serving_green) is not bool or type(intervention_active) is not bool:
            raise ValueError('signal/intervention flags must be boolean')
        if forecast.edge_id!=o.edge_id:
            raise ValueError('forecast edge mismatch')
        state=self.states.setdefault(o.edge_id,{'last':None,'start':None,'green_start':None,'phase_age':None})
        if state['last'] is not None and o.sim_time_s<=state['last']:
            raise ValueError('trigger clock must increase')
        if state['last'] is not None and o.sim_time_s-state['last']>self.max_gap_s:
            state['start']=state['green_start']=None
        if not serving_green or phase_age_s<5 or (state['phase_age'] is not None and phase_age_s<state['phase_age']):
            state['green_start']=None
        state['phase_age']=phase_age_s if serving_green else None
        state['last']=o.sim_time_s
        evidence_ok=(not intervention_active and forecast.usable_for_control and forecast.predicted_slowdown is not None
                     and o.coverage=='fresh' and o.slowdown is not None and o.slowdown>=self.minimum
                     and ('fixed' in o.sources or o.fresh_probes>=2) and forecast.predicted_slowdown>=self.danger)
        if not evidence_ok:
            state['start']=state['green_start']=None
            return TriggerDecision(False,0,'intervention_active' if intervention_active else 'insufficient_predictive_evidence')
        if state['start'] is None:
            state['start']=o.sim_time_s
        duration=o.sim_time_s-state['start']
        if serving_green and phase_age_s>=5 and state['green_start'] is None:
            state['green_start']=o.sim_time_s
        served=state['green_start'] is not None and o.sim_time_s-state['green_start']>=self.green_evidence_s
        eligible=duration>=self.persistence_s and served
        return TriggerDecision(bool(eligible),duration,'eligible_first_response' if eligible else 'awaiting_persistence_or_serving_phase')
