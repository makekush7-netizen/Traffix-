import pytest

from backend.replay import MatchedReplay


def test_hash_mismatch_blocked_and_no_future_frame():
    manifest = dict(network='abc', demand='def', scenario='ghi', sensor_mask='jkl', seed=7, sumo_version='v1')
    frames = [dict(sim_time_s=t, label='fixture') for t in [0, 5, 10]]
    replay = MatchedReplay(manifest, manifest.copy(), frames)
    assert replay.at(9)['sim_time_s'] == 5
    assert replay.at(4)['sim_time_s'] == 0
    assert replay.at(-1) is None
    assert replay.at(9)['source'] == 'RECORDED'
    with pytest.raises(ValueError, match='manifest_mismatch'):
        MatchedReplay(manifest, dict(manifest, demand='altered'), frames)
    with pytest.raises(ValueError, match='missing_manifest'):
        MatchedReplay({}, {}, frames)
