"""Assumed seeded arrival manifest; demand does not depend on any camera."""
import random
import math

MIX={'car':.32,'motorcycle':.35,'auto':.15,'erickshaw':.08,'bus':.04,'delivery':.06}
PRESETS={'quiet':600,'normal':1400,'busy':2400}

def generate_demand(routes, *, seed, rate, duration, mix=None):
    mix=dict(MIX if mix is None else mix)
    if not routes or any(not r for r in routes): raise ValueError('empty_routes')
    if not isinstance(seed,int) or not 0<=seed<=999999: raise ValueError('invalid_seed')
    if not math.isfinite(rate) or not 0<=rate<=10000 or not 0<duration<=3600: raise ValueError('invalid_demand')
    if set(mix)-set(MIX) or any(not math.isfinite(v) or v<0 for v in mix.values()) or abs(sum(mix.values())-1)>1e-6:
        raise ValueError('invalid_proportions')
    if rate==0: return []
    rng=random.Random(seed); rows=[]; t=0
    while t<duration:
        kind=rng.choices(list(mix),weights=list(mix.values()))[0]
        rows.append({'id':f'{kind}.{len(rows)}','type':kind,'route':rng.randrange(len(routes)),
                     'depart_s':round(t,2),'speed_factor':round(rng.uniform(.9,1.1),3)})
        t+=rng.expovariate(rate/3600)
    return rows
