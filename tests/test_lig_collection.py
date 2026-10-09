import json
import pandas as pd
from eval.cohort import fingerprint
from eval.collect import collect_results
from tests.test_compare import result

def test_collection_preserves_exported_frozen_hashes_when_objects_not_duplicated(tmp_path):
    folder=tmp_path/'run';folder.mkdir()
    metadata=result('fixed',100)
    metadata.update(teleported=0,collisions=0,scheduled_cohort_size=1)
    for key in ['comparison_config_sha256','emission_assumptions_sha256','probe_assignment_sha256']:
        metadata[key]=fingerprint(key)
    (folder/'manifest.json').write_text(json.dumps(metadata))
    pd.DataFrame([dict(vehicle_id='car.0',scheduled_depart_s=0,actual_depart_s=0,arrival_s=100,
                       status='arrived',co2_mg=1000)]).to_csv(folder/'trips.csv',index=False)
    output=collect_results(tmp_path)
    assert not output['errors']
    assert output['results'][0]['comparison_config_sha256']==metadata['comparison_config_sha256']
    assert output['results'][0]['emission_assumptions_sha256']==metadata['emission_assumptions_sha256']
