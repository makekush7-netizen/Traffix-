"""Aggregate validated uplinks only. Authentication belongs to the backend gateway."""
from collections import deque
from dataclasses import asdict, dataclass
from math import isfinite
from statistics import median
from typing import Mapping
from numbers import Real


def finite(value, name, minimum=0):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a number")
    value = float(value)
    if not isfinite(value) or value < minimum:
        raise ValueError(f"{name} must be finite and >= {minimum}")
    return value


@dataclass(frozen=True)
class ProbeSample:
    vehicle_id: str
    edge_id: str
    sim_time_s: float
    speed_mps: float
    source: str = "phone"

    def __post_init__(self):
        if not isinstance(self.vehicle_id,str) or not isinstance(self.edge_id,str) or not self.vehicle_id or not self.edge_id:
            raise ValueError("vehicle and edge IDs are required")
        finite(self.sim_time_s, "sample time")
        finite(self.speed_mps, "speed")
        if self.source not in {"phone", "emulated_probe"}:
            raise ValueError("invalid probe source")


@dataclass(frozen=True)
class EdgeObservation:
    edge_id: str
    sim_time_s: float
    coverage: str
    sources: tuple[str, ...]
    mean_speed_mps: float | None
    slowdown: float | None
    distinct_probes_60s: int
    sample_age_sim_s: float | None
    fixed_queue_ratio: float | None = None
    fresh_probes: int = 0

    def __post_init__(self):
        if not isinstance(self.edge_id,str) or not self.edge_id:
            raise ValueError('edge ID is required')
        if any(source not in {'phone','emulated_probe','fixed'} for source in self.sources):
            raise ValueError('invalid observation source')
        finite(self.sim_time_s, "observation time")
        for count in [self.distinct_probes_60s, self.fresh_probes]:
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ValueError("probe counts must be nonnegative integers")
        if self.fresh_probes > self.distinct_probes_60s:
            raise ValueError("fresh probes cannot exceed window count")
        if self.coverage not in {"fresh", "stale", "unknown"}:
            raise ValueError("invalid coverage")
        for name in ["mean_speed_mps", "slowdown", "sample_age_sim_s", "fixed_queue_ratio"]:
            v = getattr(self, name)
            if v is not None:
                finite(v, name)
                if name in {"slowdown", "fixed_queue_ratio"} and v > 1:
                    raise ValueError(f"{name} must be <= 1")
        if self.coverage != "fresh" and self.slowdown is not None:
            raise ValueError("stale/unknown observations cannot carry current slowdown")

    def to_payload(self):
        result = asdict(self)
        result.pop("sim_time_s")
        result.pop("fresh_probes")
        result["sources"] = list(self.sources)
        return result

    @classmethod
    def from_mapping(cls, row: Mapping):
        def optional(name):
            value = row.get(name)
            if value is None or value == "":
                return None
            try:
                parsed=float(value)
                if parsed != parsed:
                    return None  # CSV NaN means a missing cell; infinity does not.
                if not isfinite(parsed):
                    raise ValueError('nonfinite value')
                return parsed
            except (ValueError, TypeError):
                raise ValueError(f"invalid {name}: {value}") from None
        sources = row.get("sources", ())
        if sources is None or isinstance(sources, float) and not isfinite(sources):
            sources = ()
        if isinstance(sources, str):
            sources = tuple(s for s in sources.split(",") if s)
        coverage = row.get("coverage", "unknown")
        def count_value(name):
            value=row.get(name,0)
            parsed=float(value)
            if isinstance(value,bool) or not isfinite(parsed) or parsed<0 or not parsed.is_integer():
                raise ValueError('probe counts must be nonnegative integers')
            return int(parsed)
        count = count_value('distinct_probes_60s')
        return cls(str(row["edge_id"]), float(row["sim_time_s"]), coverage, tuple(sources),
                   optional("mean_speed_mps"), optional("slowdown"), count, optional("sample_age_sim_s"),
                   optional("fixed_queue_ratio"), count_value('fresh_probes'))


class ObservationAggregator:
    """One latest fresh sample per vehicle. Never fills a gap from simulation truth."""
    def __init__(self, reference_speeds, *, allowed_fixed_edges=(), max_age_s=15, window_s=60):
        self.reference_speeds = dict(reference_speeds)
        if any(finite(v, "reference speed") == 0 for v in self.reference_speeds.values()):
            raise ValueError("reference speed must be positive")
        self.allowed_fixed_edges = set(allowed_fixed_edges)
        self.max_age_s = finite(max_age_s, "max age")
        self.window_s = finite(window_s, "window")
        self.samples = deque(maxlen=100000)
        self.last_time = {}
        self.fixed = {}

    def add_probe(self, sample):
        if sample.edge_id not in self.reference_speeds:
            raise ValueError("unknown edge")
        if sample.sim_time_s <= self.last_time.get(sample.vehicle_id, -1):
            return False
        self.last_time[sample.vehicle_id] = sample.sim_time_s
        self.samples.append(sample)
        return True

    def add_fixed(self, edge_id, sim_time_s, speed_mps, queue_ratio=None):
        if edge_id not in self.allowed_fixed_edges:
            raise ValueError("fixed sensor not permitted on this edge")
        finite(sim_time_s, "time")
        finite(speed_mps, "speed")
        if queue_ratio is not None and not 0 <= finite(queue_ratio, "queue ratio") <= 1:
            raise ValueError("invalid queue ratio")
        if edge_id not in self.reference_speeds:
            raise ValueError("unknown edge")
        if sim_time_s >= self.fixed.get(edge_id, (-1, 0, None))[0]:
            self.fixed[edge_id] = (sim_time_s, speed_mps, queue_ratio)

    def snapshot(self, edge_id, now):
        finite(now, "time")
        if edge_id not in self.reference_speeds:
            raise ValueError("unknown edge")
        latest = {}
        for s in self.samples:
            if now-self.window_s <= s.sim_time_s <= now:
                latest[s.vehicle_id] = s
        latest = {vehicle:s for vehicle,s in latest.items() if s.edge_id == edge_id}
        fresh = [s for s in latest.values() if now-s.sim_time_s <= self.max_age_s]
        fixed = self.fixed.get(edge_id)
        if fixed and fixed[0] > now:
            fixed = None
        fixed_fresh = fixed is not None and now-fixed[0] <= self.max_age_s
        sources = {s.source for s in fresh}
        speed = median(s.speed_mps for s in fresh) if fresh else None
        queue = None
        times = [s.sim_time_s for s in latest.values()]
        if fixed is not None:
            times.append(fixed[0])
        if fixed_fresh:
            speed, queue = fixed[1:]
            sources.add("fixed")
        selected_time = fixed[0] if fixed_fresh else max(times) if times else None
        coverage = "fresh" if speed is not None else ("stale" if times else "unknown")
        slowdown = None if speed is None else max(0.0, min(1.0, 1-speed/self.reference_speeds[edge_id]))
        return EdgeObservation(edge_id, now, coverage, tuple(sorted(sources)), speed, slowdown,
                               len(latest), now-selected_time if selected_time is not None else None, queue, len(fresh))
