"""Explicit-demand and SUMO tripinfo import; missing output never hides a vehicle.

Reference: https://sumo.dlr.de/docs/Simulation/Output/TripInfo.html
CO2_abs is mg, not a rate. Missing tripinfo needs the worker's lifecycle log.
"""
from dataclasses import fields
from pathlib import Path
import xml.etree.ElementTree as ET
import pandas as pd
from eval.cohort import Trip


def optional_number(value):
    return None if value is None or pd.isna(value) or value == '' else float(value)


def read_trips_csv(path):
    data = pd.read_csv(path)
    required = {'vehicle_id','scheduled_depart_s','actual_depart_s','arrival_s','status'}
    if not required.issubset(data.columns):
        raise ValueError(f'missing trip columns: {sorted(required-set(data.columns))}')
    defaults = {f.name: f.default for f in fields(Trip) if f.name not in required}
    trips=[]
    for row in data.to_dict('records'):
        values = {k:row.get(k,v) for k,v in defaults.items()}
        values.update({k:row[k] for k in required})
        for key in ['scheduled_depart_s','actual_depart_s','arrival_s','waiting_s','co2_mg','route_length_m']:
            values[key] = optional_number(values[key])
        if values['waiting_s'] is None:
            values['waiting_s'] = 0.0
        if values['vtype_id'] is None or pd.isna(values['vtype_id']):
            values['vtype_id']='unknown'
        trips.append(Trip(**values))
    if len({t.vehicle_id for t in trips}) != len(trips):
        raise ValueError('duplicate vehicle in trips CSV')
    return trips


def read_demand_xml(path):
    root=ET.parse(path).getroot()
    if root.findall('flow') or root.findall('personFlow') or root.findall('person'):
        raise ValueError('use explicit vehicle/trip demand; expand flows and omit person demand first')
    demand={}
    for element in list(root.findall('vehicle'))+list(root.findall('trip')):
        vehicle=element.attrib['id']
        if vehicle in demand:
            raise ValueError('duplicate explicit vehicle')
        try:
            depart=float(element.attrib['depart'])
        except (KeyError,ValueError):
            raise ValueError('explicit numeric scheduled depart is required') from None
        trip=Trip(vehicle,depart,None,None,'pending',vtype_id=element.get('type','unknown'))
        demand[vehicle]=trip
    if not demand:
        raise ValueError('empty explicit demand')
    return demand


def import_tripinfo(demand_xml, tripinfo_xml, *, lifecycle_csv=None):
    demand=read_demand_xml(demand_xml)
    lifecycle={}
    if lifecycle_csv is not None:
        data=pd.read_csv(lifecycle_csv)
        required={'vehicle_id','status','actual_depart_s','arrival_s'}
        if not required.issubset(data.columns) or data.vehicle_id.duplicated().any():
            raise ValueError('invalid lifecycle CSV')
        lifecycle={row['vehicle_id']:row for row in data.to_dict('records')}
        if set(lifecycle)-set(demand):
            raise ValueError('lifecycle contains vehicle outside scheduled cohort')
    parsed={}
    for element in ET.parse(tripinfo_xml).getroot().findall('tripinfo'):
        vehicle=element.attrib['id']
        if vehicle not in demand or vehicle in parsed:
            raise ValueError('unknown or duplicate tripinfo vehicle')
        actual=float(element.attrib['depart'])
        arrival=float(element.attrib['arrival'])
        actual=None if actual<0 else actual
        arrival=None if arrival<0 else arrival
        vaporized=element.get('vaporized','false').lower()
        removal_reasons={'true','1','calibrator','gui','collision','vaporizer','traci','teleport'}
        if vaporized not in removal_reasons | {'','false','0','end'}:
            raise ValueError('unrecognized vaporized flag; supply normalized lifecycle/trips CSV')
        removed=vaporized in removal_reasons
        if vaporized=='end' and arrival is not None:
            raise ValueError('unfinished end marker contradicts arrival time')
        status='removed' if removed else ('arrived' if arrival is not None else ('active' if actual is not None else 'pending'))
        emissions=element.find('emissions')
        co2=optional_number(emissions.get('CO2_abs')) if emissions is not None else None
        parsed[vehicle]=Trip(vehicle,demand[vehicle].scheduled_depart_s,actual,None if removed else arrival,status,
                             float(element.get('waitingTime',0)),co2,element.get('vType',element.get('vtype',demand[vehicle].vtype_id)),optional_number(element.get('routeLength')))
    for vehicle in set(demand)-set(parsed):
        if vehicle not in lifecycle:
            raise ValueError(f'missing tripinfo for {vehicle}: lifecycle CSV required, cannot assume pending')
        row=lifecycle[vehicle]
        if row['status']=='arrived':
            raise ValueError('arrived lifecycle without final tripinfo: incomplete export')
        parsed[vehicle]=Trip(vehicle,demand[vehicle].scheduled_depart_s,optional_number(row['actual_depart_s']),
                             optional_number(row['arrival_s']),row['status'],vtype_id=demand[vehicle].vtype_id)
    for vehicle,row in lifecycle.items():
        if row['status'] != parsed[vehicle].status:
            raise ValueError('tripinfo and lifecycle status mismatch')
        if optional_number(row['actual_depart_s']) != parsed[vehicle].actual_depart_s or optional_number(row['arrival_s']) != parsed[vehicle].arrival_s:
            raise ValueError('tripinfo and lifecycle times mismatch')
    return [parsed[v] for v in demand]
