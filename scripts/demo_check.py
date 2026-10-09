"""Local release gate. Separate smoke process; no access to the live TraCI connection."""
import argparse
import json
from pathlib import Path
import socket
import subprocess
import sys
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main(port):
    checks=[]
    def check(name,fn):
        try: note=fn(); checks.append((name,True,str(note)))
        except Exception as exc: checks.append((name,False,str(exc)))
    def environment():
        import sumo,traci
        binary=Path(sumo.SUMO_HOME)/'bin/sumo.exe'
        if not binary.exists(): binary=Path(sumo.SUMO_HOME)/'bin/sumo'
        result=subprocess.run([str(binary),'--version'],capture_output=True,text=True,check=True)
        return result.stdout.splitlines()[0]+'; TraCI import OK'
    check('SUMO / TraCI',environment)
    def addresses():
        ips=[ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith(('127.','169.254.'))]
        if not ips: raise RuntimeError('No LAN IPv4 address found')
        return ' | '.join(f'http://{ip}:{port}/driver' for ip in sorted(ips))
    check('LAN IP and phone URLs',addresses)
    def reachable():
        with socket.create_connection(('127.0.0.1',port),timeout=3): pass
        with urllib.request.urlopen(f'http://localhost:{port}/driver',timeout=5) as r:
            if r.status!=200: raise RuntimeError('Driver page not reachable')
        with urllib.request.urlopen(f'http://localhost:{port}/api/state',timeout=5) as r:
            state=json.load(r)
        if not state.get('demo'): raise RuntimeError('Wrong server: launch scripts/run_mobile.ps1')
        from backend.harness.demo_engine import load_demo_config
        import hashlib
        expected=hashlib.sha256(json.dumps(load_demo_config(),sort_keys=True).encode()).hexdigest()
        if state['result']['scenario_sha256']!=expected: raise RuntimeError('Server configuration is stale; restart scripts/run_mobile.ps1')
        return f'Port {port} reachable; demo ready; simulated time {state["sim_time_s"]:.2f}s'
    check('Server and driver page',reachable)
    def smoke():
        result=subprocess.run([sys.executable,str(ROOT/'scripts/check_demo.py'),'--repeats','1',
                               '--output','runs/demo-check-smoke.json'],cwd=ROOT,capture_output=True,text=True,timeout=90)
        (ROOT/'runs/demo-check-smoke.log').write_text(result.stdout+result.stderr,encoding='utf-8')
        if result.returncode: raise RuntimeError('Headless demo failed; see runs/demo-check-smoke.log')
        row=json.loads((ROOT/'runs/demo-check-smoke.json').read_text())[0]
        return f'{row["arrived"]}/{row["scheduled"]} arrived; {row["collisions"]} collisions; {row["teleports"]} teleports; {row["unfinished"]} unfinished'
    check('Headless demo smoke',smoke)
    for name,ok,note in checks: print(('PASS' if ok else 'FAIL')+': '+name+' - '+note)
    output=ROOT/'runs/demo-check.json';output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps([dict(check=n,passed=ok,note=note) for n,ok,note in checks],indent=2),encoding='utf-8')
    return 0 if all(ok for _,ok,_ in checks) else 1


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8002);raise SystemExit(main(p.parse_args().port))
