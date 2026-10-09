import xml.etree.ElementTree as ET
import pytest
from backend.harness.engine import HarnessEngine


def test_harness_accepts_explicit_bounded_run_configuration():
    engine=HarnessEngine(run_config={'profile':'conservative','demand_end_s':900,'horizon_s':1200,'max_end_s':2400,'warmup_s':0})
    assert engine.run_config['max_end_s']==2400
    assert engine.run_config['warmup_s']==0


@pytest.mark.parametrize('config',[
    {'horizon_s':1200,'max_end_s':1000},
    {'step_s':0},
    {'profile':'hide_collisions'},
    {'incident_start_s':300,'incident_end_s':200},
])
def test_harness_rejects_invalid_configuration_before_starting_sumo(config):
    with pytest.raises(ValueError):
        HarnessEngine(run_config=config)


def test_demand_is_frozen_before_simulation_and_repeatable():
    from backend.harness.configuration import create_demand, normalized_config
    config=normalized_config({'demand_end_s':60,'demand_per_hour':600})
    first=create_demand(42,config);second=create_demand(42,config)
    assert ET.tostring(first)==ET.tostring(second)
    vehicles=first.findall('vehicle')
    assert len(vehicles)>0 and all(float(v.get('depart'))<60 for v in vehicles)
    kinds={v.get('id'):v for v in first.findall('vType')}
    assert set(kinds)=={'car','motorcycle','auto','erickshaw','bus','delivery'}
    assert float(kinds['motorcycle'].get('minGap'))>=2.5
    assert kinds['motorcycle'].get('latAlignment')=='center'
