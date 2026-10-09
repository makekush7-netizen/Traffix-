"""Build the offline LIG Square harness from the checked-in OSM extract."""
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'backend/harness/data'
sys.path.insert(0, str(ROOT))


def main():
    import sumo
    import sumolib
    binary = Path(sumo.SUMO_HOME) / 'bin/netconvert.exe'
    result = subprocess.run([str(binary), '--osm-files', str(DATA / 'lig.osm.xml'),
        '--node-files', str(DATA / 'lig-joins.nod.xml'),
        '--output-file', str(DATA / 'lig.net.xml'), '--lefthand', '--geometry.remove',
        '--junctions.join', '--tls.guess', '--tls.discard-simple',
        '--tls.default-type', 'static', '--tls.layout', 'incoming',
        '--tls.green.time', '30', '--tls.yellow.time', '3',
        '--tls.allred.time', '8', '--no-turnarounds', '--remove-edges.isolated',
        '--keep-edges.by-type', 'highway.primary,highway.primary_link,highway.secondary,highway.secondary_link,highway.tertiary,highway.tertiary_link,highway.residential,highway.unclassified,highway.service,highway.trunk,highway.trunk_link,highway.living_street',
        '--keep-edges.in-geo-boundary', '75.882,22.727,75.898,22.741',
        '--output.street-names', '--no-warnings'], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr)
    net = sumolib.net.readNet(str(DATA / 'lig.net.xml'), withInternal=True)
    center = net.convertLonLat2XY(75.89011, 22.73360)
    if max(abs(value) for value in center)>10000:
        raise RuntimeError('Unexpected network origin: check explicit join coordinates')
    def xy(point):
        return [round(point[0] - center[0], 2), round(point[1] - center[1], 2)]
    roads = []
    for edge in net.getEdges(withInternal=True):
        lanes = [dict(id=lane.getID(), width=lane.getWidth(), shape=[xy(p) for p in lane.getShape()]) for lane in edge.getLanes()]
        roads.append(dict(id=edge.getID(), name=edge.getName(), internal=edge.getFunction() == 'internal',
                          shape=[xy(p) for p in edge.getShape()], lanes=lanes,
                          width=sum(l['width'] for l in lanes), speed=edge.getSpeed()))
    junctions = [dict(id=node.getID(), shape=[xy(p) for p in node.getShape()],
                      position=xy(node.getCoord()), signal=node.getType() == 'traffic_light')
                 for node in net.getNodes()]
    osm = ET.parse(DATA / 'lig.osm.xml').getroot()
    osm_nodes = {n.get('id'): (float(n.get('lon')), float(n.get('lat'))) for n in osm.findall('node')}
    buildings, parks, labels = [], [], []
    rng = random.Random(42)
    for way in osm.findall('way'):
        tags = {tag.get('k'): tag.get('v') for tag in way.findall('tag')}
        points = [xy(net.convertLonLat2XY(*osm_nodes[n.get('ref')])) for n in way.findall('nd') if n.get('ref') in osm_nodes]
        if len(points) < 3 or any(abs(p[0]) > 1500 or abs(p[1]) > 1500 for p in points):
            continue
        if 'building' in tags:
            try:
                height = float(tags.get('height', '').replace('m','').strip()) if tags.get('height') else float(tags.get('building:levels','3')) * 3
            except ValueError:
                height = 9
            buildings.append(dict(id=way.get('id'), shape=points, height=min(55,max(3,height)),
                                  measured=bool(tags.get('height')), tone=rng.randrange(4), name=tags.get('name','')))
        if tags.get('leisure') in ('park','garden','playground') or tags.get('landuse') in ('grass','forest','recreation_ground'):
            parks.append(dict(shape=points, name=tags.get('name','')))
    for node in osm.findall('node'):
        tags = {t.get('k'): t.get('v') for t in node.findall('tag')}
        if tags.get('name') and (tags.get('place') or tags.get('amenity') in ('hospital','school')):
            position=xy(net.convertLonLat2XY(float(node.get('lon')),float(node.get('lat'))))
            if abs(position[0]) < 900 and abs(position[1]) < 900:
                labels.append(dict(name=tags['name'], position=position))
    # Generate connected, class-eligible routes crossing the scene.
    classes=('passenger','motorcycle','bus','delivery')
    edges=[e for e in net.getEdges(withInternal=False) if all(e.allows(c) for c in classes) and e.getLength()>35]
    outer=[e for e in edges if sum(p*p for p in xy(e.getShape()[len(e.getShape())//2])) > 450**2]
    routes=[]
    for _ in range(900):
        a,b=rng.sample(outer,2)
        if sum((x-y)**2 for x,y in zip(a.getFromNode().getCoord(),b.getToNode().getCoord())) < 650**2:
            continue
        route,cost=net.getShortestPath(a,b,vClass='passenger')
        if not route or len(route)<3 or cost>2800:
            continue
        near=min(sum(p*p for p in xy(e.getShape()[len(e.getShape())//2])) for e in route)
        if near > 160**2:
            continue
        ids=[e.getID() for e in route]
        if any(e.getFunction()=='internal' or not all(e.allows(c) for c in classes) for e in route):
            continue
        if any(not any(connection.getFromLane().allows(c) and connection.getToLane().allows(c)
                       for connection in aedge.getConnections(bedge))
               for aedge,bedge in zip(route,route[1:]) for c in classes):
            continue
        if ids not in routes:
            routes.append(ids)
        if len(routes)>=70: break
    if len(routes)<8:
        raise RuntimeError(f'Insufficient connected routes: {len(routes)}')
    candidates=[e for e in edges if len(e.getLanes())>=2 and any(t in e.getType() for t in ('primary','secondary','trunk'))]
    incident_edge=min(candidates,key=lambda e:sum(p*p for p in xy(e.getShape()[len(e.getShape())//2])))
    provenance=dict(source='OpenStreetMap', attribution='© OpenStreetMap contributors',
                    source_url='https://www.openstreetmap.org/#map=16/22.73360/75.89011',
                    downloaded_at='2026-10-09', osm_sha256=hashlib.sha256((DATA/'lig.osm.xml').read_bytes()).hexdigest(),
                    sumo_version='1.28.0', left_hand=True, calibrated=False,
                    note='OSM road geometry; inferred lane/signal defaults and building heights; synthetic traffic demand.')
    world=dict(name='LIG Square', city='Indore, Madhya Pradesh', center=list(center),
               provenance=provenance, roads=roads,junctions=junctions,buildings=buildings,parks=parks,labels=labels,
               routes=routes,incident_edge=incident_edge.getID())
    (DATA/'world.json').write_text(json.dumps(world,separators=(',',':')),encoding='utf-8')
    print(json.dumps(dict(roads=len(roads),junctions=len(junctions),buildings=len(buildings),routes=len(routes),incident_edge=incident_edge.getID(),center=center)))


if __name__=='__main__': main()
