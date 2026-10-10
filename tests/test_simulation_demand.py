from backend.simulation.demand import generate_demand
import pytest

def test_deterministic_multi_approach_demand_and_validation():
    routes=[['west','out'],['north','out']]
    a=generate_demand(routes,seed=2,rate=3600,duration=20)
    assert a==generate_demand(routes,seed=2,rate=3600,duration=20)
    assert {v['route'] for v in a}=={0,1}
    assert generate_demand(routes,seed=2,rate=0,duration=20)==[]
    with pytest.raises(ValueError): generate_demand(routes,seed=2,rate=-1,duration=20)
    with pytest.raises(ValueError): generate_demand(routes,seed=2,rate=1,duration=20,mix={'car':.4})
