"""Whole scheduled-cohort accounting, including entry waiting and detour duration."""
from dataclasses import dataclass
from math import isfinite
from statistics import mean
import numpy as np
import json
from hashlib import sha256


def fingerprint(value):
    return sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class Trip:
    vehicle_id: str
    scheduled_depart_s: float
    actual_depart_s: float | None
    arrival_s: float | None
    status: str
    waiting_s: float = 0
    co2_mg: float | None = None
    vtype_id: str = "unknown"
    route_length_m: float | None = None

    def __post_init__(self):
        if not isinstance(self.vehicle_id,str) or not self.vehicle_id or not isinstance(self.vtype_id,str) or not self.vtype_id or self.status not in {"pending", "active", "arrived", "removed"}:
            raise ValueError("invalid vehicle or trip status")
        for name in ["scheduled_depart_s", "actual_depart_s", "arrival_s", "waiting_s", "co2_mg", "route_length_m"]:
            v = getattr(self, name)
            if v is not None and (not isfinite(float(v)) or v < 0):
                raise ValueError(f"invalid {name}")
        if self.actual_depart_s is not None and self.actual_depart_s < self.scheduled_depart_s:
            raise ValueError("actual departure precedes scheduled departure")
        if self.arrival_s is not None and (self.actual_depart_s is None or self.arrival_s < self.actual_depart_s):
            raise ValueError("arrival precedes departure")
        if self.status == "arrived" and self.arrival_s is None:
            raise ValueError("arrived trip needs an arrival time")
        if self.status != "arrived" and self.arrival_s is not None:
            raise ValueError("only arrived trips have arrival times")
        if self.status == "pending" and self.actual_depart_s is not None:
            raise ValueError("pending trip cannot have departed")
        if self.status == "active" and self.actual_depart_s is None:
            raise ValueError("active trip needs departure time")


def summarize_cohort(trips, *, teleported=0, excluded_vehicle_ids=()):
    trips = list(trips)
    ids = [t.vehicle_id for t in trips]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate vehicle in cohort")
    if not isinstance(teleported, int) or teleported < 0:
        raise ValueError("invalid teleport count")
    exclusions=sorted(set(excluded_vehicle_ids))
    trips = [t for t in trips if t.vehicle_id not in set(exclusions)]
    counts = {status: sum(t.status == status for t in trips) for status in ["pending", "active", "arrived", "removed"]}
    complete = bool(trips) and counts["arrived"] == len(trips)
    valid = complete and teleported == 0 and counts["removed"] == 0
    journeys = [t.arrival_s-t.scheduled_depart_s for t in trips] if complete else []
    emissions_known = complete and all(t.co2_mg is not None for t in trips)
    return {"scheduled": len(trips), "departed": sum(t.actual_depart_s is not None for t in trips), **counts,
            "teleported": teleported, "complete": complete, "valid": valid,
            "mean_journey_s": mean(journeys) if valid else None,
            "p95_journey_s": float(np.percentile(journeys,95)) if valid else None,
            "total_wait_s": sum(t.waiting_s for t in trips),
            "co2_kg_so_far": sum(t.co2_mg or 0 for t in trips)/1e6,
            "co2_kg_final": sum(t.co2_mg for t in trips)/1e6 if emissions_known and valid else None,
            "emissions_complete": emissions_known,
            "completion_fraction": counts["arrived"]/len(trips) if trips else 0,
            "excluded": len(ids)-len(trips),
            'metric_cohort_sha256':fingerprint(sorted((t.vehicle_id,float(t.scheduled_depart_s),t.vtype_id) for t in trips)),
            'excluded_vehicle_ids_sha256':fingerprint(exclusions)}


def integrate_co2(rates_mg_s, *, step_s):
    rates = list(rates_mg_s)
    if not isfinite(float(step_s)) or step_s <= 0 or any(not isfinite(float(v)) or v < 0 for v in rates):
        raise ValueError("invalid emission rate or step")
    return sum(rates)*step_s/1e6
