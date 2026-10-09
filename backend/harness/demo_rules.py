"""Rule prototype. Inputs are admitted observations, never vehicle truth."""
import math

STAGES=('Blind spot','Phones see','Traffix decides','Driver follows')


class DemoRules:
    def __init__(self):
        self.enabled=False
        self.since=None
        self.last=None

    def set_enabled(self, enabled):
        self.enabled=bool(enabled)
        self.since=self.last=None

    def update(self, observation, now):
        eligible=(self.enabled and observation['coverage']=='fresh' and
                  observation.get('fresh_probes',0)>=2 and observation.get('slowdown') is not None and
                  observation['slowdown']>=.45)
        if not eligible:
            self.since=self.last=None
            return None
        if self.last is not None and (now<self.last or now-self.last>15): self.since=None
        if self.since is None: self.since=now
        self.last=now
        if now-self.since<30: return None
        return dict(edge_id=observation['edge_id'],phones=observation['fresh_probes'],
                    slowdown=observation['slowdown'],duration_s=now-self.since,
                    evidence=f"{observation['fresh_probes']} phones report speeds {round(observation['slowdown']*100)}% below the assumed reference for {int(now-self.since)} s")


def road_colour(row):
    if row.get('coverage')!='fresh' or row.get('slowdown') is None: return 'unknown'
    return 'alert' if row['slowdown']>=.7 else 'slow' if row['slowdown']>=.4 else 'observed'


def comparison(live, recording):
    unavailable=dict(available=False,reason='Comparison unavailable')
    if not recording: return unavailable
    baseline=recording.get('manifest',{})
    keys=('seed','scenario_sha256','network_sha256','demand_sha256')
    if any(live.get(k) is None or live.get(k)!=baseline.get(k) for k in keys): return unavailable
    for manifest in (live,baseline):
        counts=manifest.get('final_counts',{})
        mean=manifest.get('mean_journey_s')
        if (not manifest.get('complete') or counts.get('collisions')!=0 or counts.get('teleports')!=0 or
                mean is None or isinstance(mean,bool) or not math.isfinite(mean) or mean<0): return unavailable
    return dict(available=True,recorded_baseline_s=baseline['mean_journey_s'],live_run_s=live['mean_journey_s'],
                reason='Matched synthetic scenario; complete cohorts; not a general traffic benefit')
