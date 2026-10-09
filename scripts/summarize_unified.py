"""Full scheduled cohort summary from saved SUMO runs; no dropped unfinished trips."""
import argparse
import json
import statistics
import xml.etree.ElementTree as ET
from pathlib import Path


def summarize(directory):
    directory = Path(directory)
    manifest = json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    demand = json.loads((directory/'demand.json').read_text(encoding='utf-8'))
    trips = {t.attrib['id']: t.attrib for t in ET.parse(directory/'trips.xml').getroot().findall('tripinfo')}
    classes = {}
    for row in demand:
        group = classes.setdefault(row['type'], {'scheduled': 0, 'arrived': 0, 'unfinished': 0, 'not_departed': 0, 'journey_s': [], 'insertion_delay_s': []})
        group['scheduled'] += 1
        trip = trips.get(row['id'])
        if trip is None:
            group['not_departed'] += 1
        elif float(trip.get('arrival', '-1')) < 0:
            group['unfinished'] += 1
        else:
            group['arrived'] += 1
            delay = float(trip.get('departDelay', '0'))
            group['journey_s'].append(float(trip['duration']) + delay)
            group['insertion_delay_s'].append(delay)
    for group in classes.values():
        journeys = group.pop('journey_s')
        delays = group.pop('insertion_delay_s')
        group['mean_arrived_journey_s'] = statistics.mean(journeys) if journeys else None
        group['mean_arrived_insertion_delay_s'] = statistics.mean(delays) if delays else None
    return {'manifest': manifest, 'classes': classes,
            'accounting': 'not_departed includes absent trip records; distinguish export loss using manifest counts',
            'headline_eligible': bool(demand) and manifest.get('integrity') == 'complete' and manifest.get('complete') is True
                and len(demand) == manifest.get('scheduled')
                and all(g['arrived'] == g['scheduled'] for g in classes.values())}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directory')
    args = parser.parse_args()
    print(json.dumps(summarize(args.directory), indent=2))
