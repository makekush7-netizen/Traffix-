import pytest
from scripts.run_unified import listen_addresses

def test_hotspot_listener_keeps_localhost_without_binding_every_interface():
    assert listen_addresses('127.0.0.1','192.168.137.1')==['127.0.0.1','192.168.137.1']
    assert listen_addresses('127.0.0.1',None)==['127.0.0.1']

@pytest.mark.parametrize('address',['0.0.0.0','127.0.0.1','169.254.1.1','172.10.21.104','8.8.8.8','::1'])
def test_hotspot_listener_rejects_non_private_or_unspecified_addresses(address):
    with pytest.raises(ValueError):listen_addresses('127.0.0.1',address)
