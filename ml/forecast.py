"""No-action first-response forecasts. Never import TraCI or offline truth here."""
from dataclasses import asdict, dataclass
from pathlib import Path
import json
import numpy as np
from ml.features import FEATURE_COLUMNS, FEATURE_VERSION, build_features

HORIZONS = (120,180,300)
TARGET_WINDOW_S = 30
DEFAULT_LABEL_STEP_S = 5


def validate_label_step(step_s):
    if isinstance(step_s,bool) or not isinstance(step_s,(int,float)) or not np.isfinite(step_s) or step_s<=0 or not float(step_s).is_integer() or TARGET_WINDOW_S % step_s:
        raise ValueError('label step must be a positive integer divisor of 30 seconds')
    return int(step_s)


def trend_prediction(current, slope, horizon_s, *, label_step_s=DEFAULT_LABEL_STEP_S):
    step=validate_label_step(label_step_s)
    projections=[np.clip(np.asarray(current)+np.asarray(slope)*(horizon_s-offset),0,1) for offset in range(0,TARGET_WINDOW_S,step)]
    return np.mean(projections,axis=0)


@dataclass(frozen=True)
class ForecastResult:
    edge_id: str
    model: str
    horizon_s: int
    predicted_slowdown: float | None
    usable_for_control: bool
    reason: str

    def to_payload(self):
        return asdict(self)


class ForecastService:
    def __init__(self, models=None, *, min_history_s=60, min_probes=2, max_age_s=15, data_source='unverified', label_step_s=DEFAULT_LABEL_STEP_S):
        self.models = models or {}
        self.data_source = data_source
        self.label_step_s=validate_label_step(label_step_s)
        self.min_history_s, self.min_probes, self.max_age_s = min_history_s, min_probes, max_age_s

    @classmethod
    def from_directory(cls, directory):
        """Load only trusted local artifacts: joblib files are executable pickle data."""
        import joblib
        import sklearn
        from hashlib import sha256
        directory = Path(directory)
        manifest = json.loads((directory/"manifest.json").read_text(encoding="utf-8"))
        if manifest["feature_columns"] != list(FEATURE_COLUMNS) or manifest.get('feature_version') != FEATURE_VERSION:
            raise ValueError("model feature contract mismatch")
        if manifest.get('sklearn_version') != sklearn.__version__ or manifest.get('horizons') != list(HORIZONS) or manifest.get('label_policy') != 'fixed_no_action':
            raise ValueError('model version, horizons or label-policy mismatch; retrain in this environment')
        models = {}
        for h in HORIZONS:
            path=directory/f'forecast-{h}.joblib'
            if sha256(path.read_bytes()).hexdigest() != manifest.get('model_sha256',{}).get(str(h)):
                raise ValueError('model checksum mismatch; do not load changed artifacts')
            models[h] = joblib.load(path)
        return cls(models,data_source=manifest.get('data_source','unverified'),label_step_s=manifest['label_step_s'])

    def predict(self, history, horizon_s, *, method="trend", intervention_active=False):
        if horizon_s not in HORIZONS or method not in {"trend","persistence","boosting"}:
            raise ValueError("unsupported horizon or method")
        history = list(history)
        if not history:
            raise ValueError("empty history")
        current = history[-1]
        def unavailable(reason):
            return ForecastResult(current.edge_id,method,horizon_s,None,False,reason)
        if intervention_active:
            return unavailable("intervention_active_no_action_forecast_disabled")
        features = build_features(history)
        if current.coverage != "fresh" or current.slowdown is None:
            return unavailable("unknown_or_stale")
        enough_probes = "fixed" in current.sources or current.fresh_probes >= self.min_probes
        age_ok = current.sample_age_sim_s is not None and current.sample_age_sim_s <= self.max_age_s
        boundary=current.sim_time_s-self.min_history_s
        bracket=next((index for index in range(len(history)-1,-1,-1) if history[index].sim_time_s<=boundary),None)
        recent=history[bracket:] if bracket is not None else history
        continuous = len(recent) >= 2 and recent[-1].sim_time_s-recent[0].sim_time_s >= self.min_history_s and all(b.sim_time_s-a.sim_time_s <= self.max_age_s for a,b in zip(recent,recent[1:]))
        usable = enough_probes and age_ok and continuous and features["fresh_fraction_60"] >= 0.8
        if method == "boosting":
            if horizon_s not in self.models:
                return unavailable("boosting_model_not_loaded")
            vector = np.array([[features[name] for name in FEATURE_COLUMNS]], dtype=float)
            from threadpoolctl import threadpool_limits
            with threadpool_limits(limits=1):
                value = float(self.models[horizon_s].predict(vector)[0])
        else:
            value = float(trend_prediction(current.slowdown,features['slowdown_slope_60'],horizon_s,label_step_s=self.label_step_s)) if method=='trend' else current.slowdown
        if not np.isfinite(value):
            return unavailable('nonfinite_prediction')
        value = max(0.0,min(1.0,value))
        if method == 'boosting' and self.data_source == 'fixture':
            return ForecastResult(current.edge_id,method,horizon_s,value,False,'fixture_model_not_for_control')
        if method == 'boosting' and self.data_source != 'sumo':
            return ForecastResult(current.edge_id,method,horizon_s,value,False,'unverified_model_data_source')
        return ForecastResult(current.edge_id,method,horizon_s,value,usable,"ready" if usable else "insufficient_history_or_coverage")
