"""In-process backend adapter. This is an internal API, not new wire message types.

Gateway must authenticate, bind vehicle IDs and validate echoed frame/time first.
Create one instance per run; call tick every five simulated seconds in the worker.
"""
from collections import deque
from dataclasses import asdict
from ml.detect import DetectionEngine
from ml.forecast import ForecastService, HORIZONS
from ml.observations import ObservationAggregator, ProbeSample, finite


class TrafficIntelligence:
    def __init__(self, run_id, reference_speeds, *, allowed_fixed_edges=(), forecaster=None, detector=None):
        self.run_id=run_id
        self.aggregator=ObservationAggregator(reference_speeds,allowed_fixed_edges=allowed_fixed_edges)
        self.detector=detector or DetectionEngine()
        self.forecaster=forecaster or ForecastService()
        self.history={edge:deque(maxlen=120) for edge in reference_speeds}
        self.last_tick=None

    def ingest_probe(self, validated_message):
        message=validated_message
        if message.get('run_id')!=self.run_id or message.get('type')!='probe.sample' or message.get('v')!=1:
            raise ValueError('wrong run or message type')
        payload=message['payload']; pose=payload['pose']
        sample=ProbeSample(payload['vehicle_id'],pose['edge_id'],message['sim_time_s'],pose['speed_mps'])
        return self.aggregator.add_probe(sample)

    def ingest_emulated_probe(self, sample):
        if sample.source != 'emulated_probe':
            raise ValueError('emulated batch data must retain source label')
        return self.aggregator.add_probe(sample)

    def tick(self, sim_time_s, signal_context, *, intervention_active=False, methods=('trend',)):
        finite(sim_time_s,'tick time')
        if self.last_tick is not None and sim_time_s<=self.last_tick:
            raise ValueError('ticks must increase; construct a new instance for a new run')
        methods=tuple(methods)
        if any(method not in {'trend','persistence','boosting'} for method in methods) or type(intervention_active) is not bool:
            raise ValueError('invalid forecast methods or intervention flag')
        for edge in self.history:
            context=signal_context.get(edge,{})
            if type(context.get('serving_green',False)) is not bool:
                raise ValueError('serving_green must be boolean')
            finite(context.get('phase_age_s',0),'phase age')
        self.last_tick=sim_time_s
        observations=[]; forecasts=[]; detections={}; events=[]; log_rows=[]
        for edge,history in self.history.items():
            observation=self.aggregator.snapshot(edge,sim_time_s)
            history.append(observation)
            context=signal_context.get(edge,{})
            state=self.detector.update(observation,serving_green=context.get('serving_green',False),phase_age_s=context.get('phase_age_s',0))
            detections[edge]=asdict(state)
            payload=observation.to_payload()
            observations.append(payload)
            events.append({'type':'observation.edge','payload':payload})
            log_rows.append({**payload,'run_id':self.run_id,'sim_time_s':sim_time_s,'fresh_probes':observation.fresh_probes,'sources':','.join(observation.sources)})
            log_rows[-1].update(serving_green=context.get('serving_green',False),phase_age_s=context.get('phase_age_s',0))
            for method in methods:
                for h in HORIZONS:
                    forecast=self.forecaster.predict(history,h,method=method,intervention_active=intervention_active).to_payload()
                    forecasts.append(forecast)
                    events.append({'type':'forecast.edge','payload':forecast})
        return {'run_id':self.run_id,'sim_time_s':sim_time_s,'observations':observations,'forecasts':forecasts,
                'detections':detections,'events':events,'log_rows':log_rows}
