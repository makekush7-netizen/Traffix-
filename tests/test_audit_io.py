import pandas as pd
from eval.io import import_tripinfo
from eval.cohort import summarize_cohort, Trip
from eval.report import write_run_report


def test_real_sumo_unfinished_marker_and_removal_are_imported(tmp_path):
    demand=tmp_path/'demand.xml';info=tmp_path/'tripinfo.xml'
    demand.write_text('<routes><vehicle id="a" depart="0" type="old"/><vehicle id="b" depart="0"/></routes>')
    info.write_text('<tripinfos><tripinfo id="a" depart="0" arrival="-1" vaporized="end" vType="new"/><tripinfo id="b" depart="0" arrival="30" vaporized="traci"/></tripinfos>')
    trips=import_tripinfo(demand,info)
    assert trips[0].status=='active' and trips[0].vtype_id=='new'
    assert trips[1].status=='removed' and not summarize_cohort(trips)['valid']


def test_teleport_marker_cannot_be_a_clean_arrival(tmp_path):
    demand=tmp_path/'demand.xml';info=tmp_path/'tripinfo.xml'
    demand.write_text('<routes><vehicle id="a" depart="0"/></routes>')
    info.write_text('<tripinfos><tripinfo id="a" depart="0" arrival="30" vaporized="teleport"/></tripinfos>')
    assert not summarize_cohort(import_tripinfo(demand,info))['valid']


def test_report_never_defaults_unknown_teleports_to_zero(tmp_path):
    trips=[Trip('a',0,0,30,'arrived',co2_mg=100)]
    report=write_run_report(trips,dict(run_id='r',data_source='sumo',scheduled_cohort_size=1),tmp_path)
    assert not report['valid'] and report['mean_journey_s'] is None
