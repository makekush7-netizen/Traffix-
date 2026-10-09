"""Cold-start the offline LIG observation/model demo with explicit source labels."""
import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--probe-mode',choices=['phone','emulated','none'],default='phone')
    p.add_argument('--policy',choices=['fixed','reactive','predictive'],default='fixed')
    p.add_argument('--scenario',choices=['everyday','rain','roadworks','rush'],default='roadworks')
    p.add_argument('--models',type=Path);p.add_argument('--selection',type=Path)
    p.add_argument('--port',type=int,default=8001)
    a=p.parse_args(argv)
    if a.policy=='predictive' and not (a.models and a.selection): p.error('predictive requires --models and --selection')
    if not 1024<=a.port<=65535: p.error('port must be 1024–65535')
    from scripts.verify_nandani import prepare_environment
    prepare_environment()
    if a.models:
        from ml.forecast import ForecastService
        service=ForecastService.from_directory(a.models)
        if service.data_source!='sumo': raise ValueError('fixture/unverified model cannot run the LIG demo')
        os.environ['TRAFFIX_MODELS']=str(a.models.resolve())
    else: os.environ.pop('TRAFFIX_MODELS',None)
    if a.selection:
        from backend.harness.policy import validated_selection
        validated_selection(json.loads(a.selection.read_text(encoding='utf-8')))
        os.environ['TRAFFIX_SELECTION']=str(a.selection.resolve())
    else: os.environ.pop('TRAFFIX_SELECTION',None)
    os.environ.update(TRAFFIX_PROBE_MODE=a.probe_mode,TRAFFIX_POLICY=a.policy,
                      TRAFFIX_INITIAL_SCENARIO=a.scenario,TRAFFIX_LIG_PROFILE='batch')
    import uvicorn
    uvicorn.run('backend.harness.app:app',host='127.0.0.1',port=a.port,workers=1)

if __name__=='__main__': main()
