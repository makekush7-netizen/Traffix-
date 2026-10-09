"""Bind validated controller selections to actual model artifacts before execution."""
from hashlib import sha256
import json
from pathlib import Path
from eval.cohort import fingerprint

def execution_artifacts(model_dir,selection):
    if model_dir is None:
        if selection is not None: raise ValueError('selection requires its model identity')
        return dict(model_manifest_sha256=None,selection_sha256=None)
    path=Path(model_dir)/'manifest.json'
    manifest_sha=sha256(path.read_bytes()).hexdigest()
    if selection is not None and selection.get('model_manifest_sha256')!=manifest_sha:
        raise ValueError('model/selection identity mismatch')
    manifest=json.loads(path.read_text(encoding='utf-8'))
    if manifest.get('data_source')!='sumo': raise ValueError('execution requires genuine SUMO models')
    for horizon,expected in manifest.get('model_sha256',{}).items():
        model=Path(model_dir)/f'forecast-{horizon}.joblib'
        if sha256(model.read_bytes()).hexdigest()!=expected: raise ValueError('model checksum identity mismatch')
    return dict(model_manifest_sha256=manifest_sha,selection_sha256=fingerprint(selection) if selection is not None else None)
