import pandas as pd
import pytest
from eval.io import import_tripinfo, read_demand_xml, read_trips_csv
from eval.cohort import summarize_cohort


def files(tmp_path):
    demand = tmp_path / 'demand.rou.xml'
    demand.write_text('<routes><vehicle id="a" depart="10" type="car"/><vehicle id="b" depart="20" type="car"/><vehicle id="c" depart="30" type="bike"/></routes>')
    info = tmp_path / 'tripinfo.xml'
    info.write_text('<tripinfos><tripinfo id="a" depart="40" arrival="110" waitingTime="20" routeLength="300" vtype="car" vaporized="false"><emissions CO2_abs="2000000"/></tripinfo><tripinfo id="b" depart="50" arrival="-1" waitingTime="10" vaporized="false"/></tripinfos>')
    return demand, info


def test_import_preserves_uninserted_and_unfinished(tmp_path):
    demand, info = files(tmp_path)
    life = tmp_path / 'lifecycle.csv'
    pd.DataFrame([dict(vehicle_id='c', status='pending', actual_depart_s=None, arrival_s=None)]).to_csv(life, index=False)
    trips = import_tripinfo(demand, info, lifecycle_csv=life)
    result = summarize_cohort(trips)
    assert result['scheduled'] == 3
    assert result['pending'] == result['active'] == result['arrived'] == 1
    assert result['mean_journey_s'] is None
    assert trips[0].arrival_s - trips[0].scheduled_depart_s == 100
    assert result['co2_kg_so_far'] == 2


def test_missing_trip_without_lifecycle_cannot_be_called_pending(tmp_path):
    demand, info = files(tmp_path)
    with pytest.raises(ValueError, match='lifecycle'):
        import_tripinfo(demand, info)


def test_implicit_flows_cannot_hide_the_cohort(tmp_path):
    demand = tmp_path / 'flow.xml'
    demand.write_text('<routes><flow id="f" begin="0" end="100" number="10"/></routes>')
    with pytest.raises(ValueError, match='explicit'):
        read_demand_xml(demand)


def test_csv_roundtrip_validates_status(tmp_path):
    path = tmp_path / 'trips.csv'
    pd.DataFrame([dict(vehicle_id='a', scheduled_depart_s=0, actual_depart_s=10, arrival_s=100, status='arrived', waiting_s=2, co2_mg=1000000)]).to_csv(path, index=False)
    assert summarize_cohort(read_trips_csv(path))['mean_journey_s'] == 100
    pd.DataFrame([dict(vehicle_id='a', scheduled_depart_s=0, actual_depart_s=10, arrival_s=None, status='arrived')]).to_csv(path, index=False)
    with pytest.raises(ValueError):
        read_trips_csv(path)
