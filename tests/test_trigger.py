from ml.trigger import FirstResponseTrigger
from ml.forecast import ForecastResult
from ml.observations import EdgeObservation


def observation(t):
    return EdgeObservation('e',t,'fresh',('phone',),6,.4,2,0,fresh_probes=2)


def forecast(usable=True):
    return ForecastResult('e','trend',180,.8,usable,'ready')


def test_predictive_trigger_waits_for_persistence_and_green():
    trigger=FirstResponseTrigger(persistence_s=20)
    assert not trigger.update(observation(0),forecast(),serving_green=False,phase_age_s=10).eligible
    assert not trigger.update(observation(10),forecast(),serving_green=False,phase_age_s=10).eligible
    assert not trigger.update(observation(20),forecast(),serving_green=False,phase_age_s=10).eligible
    assert not trigger.update(observation(25),forecast(),serving_green=True,phase_age_s=5).eligible
    assert trigger.update(observation(35),forecast(),serving_green=True,phase_age_s=15).eligible


def test_missing_evidence_resets_and_intervention_blocks_new_prediction():
    trigger=FirstResponseTrigger(persistence_s=20)
    trigger.update(observation(0),forecast(),serving_green=True,phase_age_s=10)
    trigger.update(observation(10),forecast(False),serving_green=True,phase_age_s=10)
    assert not trigger.update(observation(20),forecast(),serving_green=True,phase_age_s=10).eligible
    assert not trigger.update(observation(40),forecast(),serving_green=True,phase_age_s=10,intervention_active=True).eligible
