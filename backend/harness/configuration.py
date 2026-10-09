"""Frozen, explicit simulation assumptions. None of these are India calibration."""
import math
import random
import xml.etree.ElementTree as ET

DEFAULTS=dict(profile='conservative',step_s=.25,warmup_s=120,demand_end_s=900,
              horizon_s=1200,max_end_s=2400,demand_per_hour=None,
              incident_start_s=60,incident_end_s=360,incident_ramp_s=0,
              incident_edge=None,sublane=True)


def normalized_config(overrides=None):
    overrides=dict(overrides or {})
    if set(overrides)-set(DEFAULTS):
        raise ValueError('unknown LIG configuration fields')
    config={**DEFAULTS,**overrides}
    if config['profile'] not in {'legacy','conservative'} or type(config['sublane']) is not bool:
        raise ValueError('invalid driving profile/sublane flag')
    for field in ['step_s','warmup_s','demand_end_s','horizon_s','max_end_s','incident_start_s','incident_end_s','incident_ramp_s']:
        value=config[field]
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:
            raise ValueError('invalid simulation time')
    if config['step_s']<=0 or 5/config['step_s']!=int(5/config['step_s']):
        raise ValueError('step must divide five-second sampling')
    if not config['warmup_s']<config['horizon_s']<=config['max_end_s'] or config['demand_end_s']>config['horizon_s']:
        raise ValueError('invalid warmup/horizon/drain configuration')
    if config['incident_start_s']>=config['incident_end_s'] or config['incident_end_s']>config['horizon_s']:
        raise ValueError('invalid incident schedule')
    if config['demand_per_hour'] is not None and (isinstance(config['demand_per_hour'],bool) or not math.isfinite(config['demand_per_hour']) or config['demand_per_hour']<=0):
        raise ValueError('invalid demand rate')
    return config


def create_demand(seed,config,*,demand_per_hour=None):
    from .engine import TYPES,WORLD
    rng=random.Random(seed)
    root=ET.Element('routes')
    for name,original in TYPES.items():
        attrs=dict(original)
        if config['profile']=='conservative':
            attrs['minGap']=str(max(2.5,float(attrs['minGap'])))
            attrs.update(latAlignment='center',minGapLat='.5')
        ET.SubElement(root,'vType',id=name,sigma='.2' if config['profile']=='conservative' else '.45',
                      speedDev='.08',lcPushy='0',lcAssertive='.5' if config['profile']=='conservative' else '1',
                      tau='2.5' if config['profile']=='conservative' else '1.5',**attrs)
    for index,edges in enumerate(WORLD['routes']):
        ET.SubElement(root,'route',id=f'route.{index}',edges=' '.join(edges))
    demand_rate=config['demand_per_hour'] or demand_per_hour or 1900
    scheduled=0;t=0
    while t<config['demand_end_s']:
        kind=rng.choices(list(TYPES),weights=[32,35,15,8,4,6])[0]
        ET.SubElement(root,'vehicle',id=f'{kind}.{scheduled}',type=kind,
                      route=f'route.{rng.randrange(len(WORLD["routes"]))}',depart=f'{t:.2f}',
                      departLane='best',departSpeed='random')
        scheduled+=1;t+=rng.expovariate(demand_rate/3600)
    return root
