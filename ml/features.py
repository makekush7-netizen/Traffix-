"""Causal feature allowlist; metadata and future labels never become predictors."""
import numpy as np

FEATURE_COLUMNS = ("slowdown_now", "slowdown_mean_30", "slowdown_mean_60", "slowdown_mean_120", "slowdown_slope_60", "distinct_probes_60s", "sample_age_sim_s", "fixed_queue_ratio", "history_span_s", "fresh_fraction_60")
FEATURE_VERSION = 2


def build_features(history):
    history = list(history)
    if not history:
        raise ValueError("observation history is empty")
    if len({o.edge_id for o in history}) != 1:
        raise ValueError("history must contain exactly one edge")
    if any(b.sim_time_s <= a.sim_time_s for a,b in zip(history, history[1:])):
        raise ValueError("history must have strictly increasing time")
    current = history[-1]
    now = current.sim_time_s
    history = [o for o in history if o.sim_time_s >= now-120]
    def fresh(window):
        return [o for o in history if now-window <= o.sim_time_s <= now and o.coverage == "fresh" and o.slowdown is not None]
    recent = fresh(60)
    times = np.array([o.sim_time_s-now for o in recent])
    values = np.array([o.slowdown for o in recent])
    slope = float(np.polyfit(times, values, 1)[0]) if len(recent) >= 2 else 0.0
    features = {"slowdown_now": np.nan if current.slowdown is None else current.slowdown,
                "slowdown_slope_60": slope, "distinct_probes_60s": current.distinct_probes_60s,
                "sample_age_sim_s": np.nan if current.sample_age_sim_s is None else current.sample_age_sim_s,
                "fixed_queue_ratio": np.nan if current.fixed_queue_ratio is None else current.fixed_queue_ratio,
                "history_span_s": now-history[0].sim_time_s,
                "fresh_fraction_60": len(recent)/max(1,len([o for o in history if o.sim_time_s >= now-60]))}
    for window in [30,60,120]:
        data = fresh(window)
        features[f"slowdown_mean_{window}"] = float(np.mean([o.slowdown for o in data])) if data else np.nan
    return {name: features[name] for name in FEATURE_COLUMNS}
