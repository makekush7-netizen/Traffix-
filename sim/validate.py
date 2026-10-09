"""
sim/validate.py — Nandani's sim validator
Acceptance test: pytest tests/test_sim_validate.py (or run directly).

Checks:
1. All referenced files exist.
2. id-registry.json fields resolve to real IDs in bazaar.net.xml.
3. Three role vehicles present in demand file with correct IDs.
4. Both routes (main_route, bypass_route) are syntactically valid.
5. SUMO runs headless for 10 simulated seconds without error.
6. det.market_mid_TRUTH is in truth_only list; NOT in operational list.
"""

import subprocess
import sys
import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path

SIM_ROOT = Path(__file__).parent
NET_DIR  = SIM_ROOT / "net"
DEMAND_DIR = SIM_ROOT / "demand"

REQUIRED_FILES = [
    NET_DIR / "bazaar.net.xml",
    NET_DIR / "bazaar.sumocfg",
    NET_DIR / "bazaar.nod.xml",
    NET_DIR / "bazaar.edg.xml",
    NET_DIR / "detectors.add.xml",
    NET_DIR / "id-registry.json",
    NET_DIR / "geometry.json",
    DEMAND_DIR / "rain_ramp.seed-042.rou.xml",
    DEMAND_DIR / "roles.rou.xml",
    SIM_ROOT / "scenarios" / "rain_ramp.json",
]

ROLE_VEHICLE_IDS = {"veh.role.rider", "veh.role.auto", "veh.role.delivery"}
ROUTE_IDS        = {"main_route", "bypass_route"}


def check_files():
    missing = [str(f) for f in REQUIRED_FILES if not f.exists()]
    assert not missing, f"Missing files:\n" + "\n".join(missing)
    print("[PASS] All required files present.")


def check_registry():
    reg = json.loads((NET_DIR / "id-registry.json").read_text())
    net = ET.parse(NET_DIR / "bazaar.net.xml").getroot()

    # Collect real edge and junction IDs from net XML
    net_edges = {e.get("id") for e in net.iter("edge") if not e.get("function")}
    net_junctions = {j.get("id") for j in net.iter("junction")}
    net_tls = {tl.get("id") for tl in net.iter("tlLogic")}

    # Check edge logical names resolve
    for logical, sumo_id in reg["edges"].items():
        if logical.startswith("_"):
            continue
        assert sumo_id in net_edges, \
            f"Registry edge '{logical}' -> '{sumo_id}' not found in net XML."

    # Check junction logical names resolve
    for logical, sumo_id in reg["junctions"].items():
        assert sumo_id in net_junctions, \
            f"Registry junction '{logical}' -> '{sumo_id}' not found in net XML."

    # Check TLS IDs
    for name, sig in reg["signals"].items():
        assert sig["sumo_id"] in net_tls, \
            f"Registry signal '{name}' -> '{sig['sumo_id']}' not found in net tlLogic."

    print("[PASS] id-registry.json — all logical names resolve to real SUMO IDs.")


def check_demand():
    # Collect vehicles and routes from all demand files
    all_vehs = {}
    route_ids = set()
    for demand_file in [DEMAND_DIR / "rain_ramp.seed-042.rou.xml", DEMAND_DIR / "roles.rou.xml"]:
        if demand_file.exists():
            root = ET.parse(demand_file).getroot()
            for v in root.iter("vehicle"):
                all_vehs[v.get("id")] = float(v.get("depart", 0))
            for r in root.iter("route"):
                route_ids.add(r.get("id"))

    # Check role vehicles
    missing_roles = ROLE_VEHICLE_IDS - set(all_vehs.keys())
    assert not missing_roles, f"Missing role vehicles: {missing_roles}"

    # Check routes
    missing_routes = ROUTE_IDS - route_ids
    assert not missing_routes, f"Missing routes: {missing_routes}"

    # Check delivery departs after rider and auto (upstream diversion logic)
    assert all_vehs["veh.role.delivery"] > all_vehs["veh.role.rider"], \
        "Delivery must depart after rider."
    assert all_vehs["veh.role.delivery"] > all_vehs["veh.role.auto"], \
        "Delivery must depart after auto."

    print("[PASS] Demand files — three role vehicles and both routes present.")


def check_detector_isolation():
    """Market detector must be truth_only; must NOT appear in operational list."""
    scenario = json.loads((SIM_ROOT / "scenarios" / "rain_ramp.json").read_text())
    truth_only = set(scenario["fixed_sensors"]["truth_only"])
    operational = set(scenario["fixed_sensors"]["operational"])

    assert "det.market_mid_TRUTH" in truth_only, \
        "det.market_mid_TRUTH must be in fixed_sensors.truth_only."
    assert "det.market_mid_TRUTH" not in operational, \
        "det.market_mid_TRUTH must NOT be in fixed_sensors.operational (truth-only rule)."

    # Also check registry
    reg = json.loads((NET_DIR / "id-registry.json").read_text())
    assert reg["detectors"]["det.market_mid_TRUTH"]["truth_only"] is True, \
        "det.market_mid_TRUTH must have truth_only=true in id-registry.json."

    print("[PASS] Market detector isolation — truth_only enforced, not in operational list.")


def check_sumo_headless(n_steps=10):
    """Run SUMO headless for n_steps seconds and verify exit code 0."""
    # Ensure output directory exists (SUMO cannot create it)
    (NET_DIR / "output").mkdir(exist_ok=True)
    cmd = [
        "sumo",
        "--seed", "42",
        "-c", str(NET_DIR / "bazaar.sumocfg"),
        "--end", str(n_steps),
        "--no-step-log",
        "--no-warnings",
        # Override output files to tmp names so validation does not pollute real runs
        "--tripinfo-output",  str(NET_DIR / "output" / "_val_trips.xml"),
        "--summary-output",   str(NET_DIR / "output" / "_val_summary.xml"),
        "--emission-output",  str(NET_DIR / "output" / "_val_emissions.xml"),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(NET_DIR))
    if result.returncode != 0:
        print("SUMO stderr:", result.stderr[-2000:])
        assert False, f"SUMO exited with code {result.returncode}"
    print(f"[PASS] SUMO headless — ran {n_steps} sim-seconds, exit 0.")


def main():
    errors = []
    checks = [
        ("file_existence",       check_files),
        ("id_registry",          check_registry),
        ("demand_roles_routes",  check_demand),
        ("detector_isolation",   check_detector_isolation),
        ("sumo_headless_10s",    check_sumo_headless),
    ]
    for name, fn in checks:
        try:
            fn()
        except Exception as exc:
            print(f"[FAIL] {name}: {exc}")
            errors.append(name)

    print()
    if errors:
        print(f"FAILED: {errors}")
        sys.exit(1)
    else:
        print("All checks passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
