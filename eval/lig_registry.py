"""Contract-safe aliases derived from the checked-in LIG SUMO network."""
from hashlib import sha256
import xml.etree.ElementTree as ET
from backend.harness.engine import DATA, WORLD

FOCUS='191621641#11'
TLS='cluster_2023505360_2023505361_2023505364_8389132295'

def load_registry():
    net=ET.parse(DATA/'lig.net.xml').getroot()
    elements={edge.attrib['id']:edge for edge in net.findall('edge')}
    connections=[c.attrib for c in net.findall('connection') if c.get('tl')==TLS]
    incoming=sorted({c['from'] for c in connections},key=lambda e:(e!=FOCUS,e))
    outgoing=sorted({c['to'] for c in connections})
    edges={}
    for prefix,ids in [('approach',incoming),('exit',outgoing)]:
        for index,actual in enumerate(ids):
            lanes=elements[actual].findall('lane')
            edges[f'edge.lig.{prefix}.{index}']=dict(sumo_id=actual,
                lanes=[lane.attrib['id'] for lane in lanes],
                length_m=float(lanes[0].get('length')),lane_count=len(lanes),
                reference_speed_mps=min(13.9,float(lanes[0].get('speed'))),
                signal_indices=sorted({int(c['linkIndex']) for c in connections if c['from']==actual}),
                receiving_edges=sorted({c['to'] for c in connections if c['from']==actual}))
    return dict(version=1,tls_id='tls.lig',tls_sumo_id=TLS,focus_edge='edge.lig.approach.0',
                network_sha256=sha256((DATA/'lig.net.xml').read_bytes()).hexdigest(),edges=edges,
                routes={f'route.{i}':route for i,route in enumerate(WORLD['routes'])},
                reference_assumption='Frozen minimum of posted limit and 13.9 m/s common fleet cap; slow rickshaw proxies are not calibrated.')

def probe_assignment(vehicle_ids,seed,participation):
    if not 0<=participation<=1:
        raise ValueError('invalid probe participation')
    return sorted(v for v in vehicle_ids if int(sha256(f'{seed}|{v}'.encode()).hexdigest()[:16],16)/2**64<participation)
