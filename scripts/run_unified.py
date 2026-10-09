"""Portable SUMO boot. The SUMO package wheel supplies tools and executable."""
import os
from pathlib import Path

def prepare_environment():
    import sumo
    home=Path(sumo.SUMO_HOME)
    os.environ['SUMO_HOME']=str(home)
    os.environ['PATH']=str(home/'bin')+os.pathsep+os.environ.get('PATH','')
    return home

def main():
    prepare_environment()
    import uvicorn
    uvicorn.run('backend.simulation.app:app',host=os.getenv('TRAFFIX_HOST','127.0.0.1'),port=int(os.getenv('TRAFFIX_PORT','8005')),workers=1)
if __name__=='__main__': main()
