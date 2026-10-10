import json
from scripts.summarize_unified import summarize


def test_incomplete_cohort_cannot_be_headline_even_if_manifest_claims_complete(tmp_path):
    (tmp_path/'manifest.json').write_text(json.dumps({'integrity':'complete','complete':True,'scheduled':3}))
    (tmp_path/'demand.json').write_text(json.dumps([{'id':i,'type':'car'} for i in ('arrived','unfinished','pending')]))
    (tmp_path/'trips.xml').write_text('<tripinfos><tripinfo id="arrived" arrival="20" duration="10" departDelay="2"/><tripinfo id="unfinished" arrival="-1" duration="5"/></tripinfos>')
    result = summarize(tmp_path)
    assert not result['headline_eligible']
    assert result['classes']['car']['arrived'] == 1
    assert result['classes']['car']['unfinished'] == 1
    assert result['classes']['car']['not_departed'] == 1
    assert result['classes']['car']['mean_arrived_journey_s'] == 12
