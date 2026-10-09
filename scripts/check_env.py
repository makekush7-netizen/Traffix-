"""Quick environment check for Trafixx. Run: python scripts/check_env.py"""
import importlib, os, shutil, subprocess, sys
from pathlib import Path

def ok(msg): print(f"[ok]   {msg}")
def bad(msg): print(f"[FAIL] {msg}")

print("Python", sys.version.split()[0])
for mod in ["fastapi", "uvicorn", "pydantic", "numpy", "pandas", "sklearn", "jsonschema", "pytest"]:
    try:
        importlib.import_module(mod); ok(mod)
    except Exception as e:
        bad(f"{mod}: {e}")

sumo_home = os.environ.get("SUMO_HOME")
if not sumo_home:
    try:
        sumo_home = importlib.import_module('sumo').SUMO_HOME
    except ImportError:
        pass
ok(f"SUMO_HOME={sumo_home}") if sumo_home else bad("SUMO_HOME is not set")
sumo = shutil.which("sumo")
if not sumo and sumo_home:
    binary = Path(sumo_home) / 'bin' / ('sumo.exe' if os.name == 'nt' else 'sumo')
    if binary.is_file():
        sumo = str(binary)
if sumo:
    out = subprocess.run([sumo, "--version"], capture_output=True, text=True).stdout.splitlines()
    ok(f"sumo found: {out[0] if out else sumo}")
else:
    bad("sumo not on PATH")
try:
    import traci  # noqa
    ok("traci importable")
except Exception:
    if sumo_home:
        sys.path.append(os.path.join(sumo_home, "tools"))
        try:
            import traci  # noqa
            ok("traci importable via SUMO_HOME/tools")
        except Exception as e:
            bad(f"traci: {e}")
    else:
        bad("traci not importable")
