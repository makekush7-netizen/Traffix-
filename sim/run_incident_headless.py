"""
sim/run_incident_headless.py — run the rain-ramp incident scenario headless.

This adds the delivery vehicle stop (obstruction on main1) and rain speed
ramp via TraCI, then saves the run to runs/<run_id>/.

AGENTS.md rule 9: never claim improvement without saved run files.
Incomplete runs are marked incomplete in manifest.json.

Usage:
    python sim/run_incident_headless.py [--seed 42] [--end 2400]
"""

import argparse
import datetime
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SIM_ROOT  = Path(__file__).parent
NET_DIR   = SIM_ROOT / "net"
RUNS_DIR  = REPO_ROOT / "runs"

# Rain speed ramp stages: (sim_time_s, speed_m/s, edges_to_restrict)
RAIN_STAGES = [
    (300, 8.0,   ["main1", "main2"]),
    (450, 6.0,   ["main1", "main2"]),
    (600, 5.0,   ["main1", "main2"]),
    (900, 13.89, ["main1", "main2"]),   # restore
]

# Delivery stop: stop veh.role.delivery at t=300 on main1_0 pos=150 for 400 s
INCIDENT_VEH      = "veh.role.delivery"
INCIDENT_LANE     = "main1_0"
INCIDENT_POS      = 150.0
INCIDENT_START_S  = 300
INCIDENT_DUR_S    = 400


def build_run_id(seed: int) -> str:
    ts = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    return f"run.bazaar.seed{seed:03d}.incident.{ts}"


def make_run_dir(run_id: str) -> Path:
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "output").mkdir(exist_ok=True)
    return run_dir


def write_manifest(run_dir: Path, seed: int, end_s: int, run_id: str,
                   complete: bool, notes: str):
    manifest = {
        "run_id":       run_id,
        "seed":         seed,
        "policy":       "incident",
        "end_s":        end_s,
        "sumocfg":      str(NET_DIR / "bazaar.sumocfg"),
        "sumo_version": "Eclipse SUMO 1.28.0",
        "complete":     complete,
        "timestamp":    datetime.datetime.now().isoformat(),
        "incident": {
            "vehicle":   INCIDENT_VEH,
            "lane":      INCIDENT_LANE,
            "pos_m":     INCIDENT_POS,
            "start_s":   INCIDENT_START_S,
            "duration_s": INCIDENT_DUR_S,
        },
        "rain_stages": [
            {"sim_s": t, "speed_mps": s, "edges": e}
            for t, s, e in RAIN_STAGES
        ],
        "notes": notes,
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


def run(seed: int, end_s: int) -> dict:
    """Run via TraCI and return result dict."""
    try:
        import traci
    except ImportError:
        return {
            "complete": False,
            "notes": "traci not importable. Install via: pip install eclipse-sumo or set SUMO_HOME.",
            "summary_rows": [],
        }

    run_id  = build_run_id(seed)
    run_dir = make_run_dir(run_id)
    (NET_DIR / "output").mkdir(exist_ok=True)

    trips_out    = str(run_dir / "output" / "trips.xml")
    summary_out  = str(run_dir / "output" / "summary.xml")
    emission_out = str(run_dir / "output" / "emissions.xml")

    sumo_cmd = [
        "sumo",
        "--seed", str(seed),
        "-c", str(NET_DIR / "bazaar.sumocfg"),
        "--end", str(end_s),
        "--no-step-log",
        "--tripinfo-output",  trips_out,
        "--summary-output",   summary_out,
        "--emission-output",  emission_out,
    ]

    print(f"[incident] run_id  : {run_id}")
    print(f"[incident] run_dir : {run_dir}")

    traci.start(sumo_cmd)

    incident_applied = False
    rain_stage_idx   = 0
    summary_rows     = []

    try:
        while traci.simulation.getMinExpectedNumber() > 0 or \
              traci.simulation.getTime() < end_s:

            traci.simulationStep()
            t = traci.simulation.getTime()

            if t > end_s:
                break

            # Apply rain speed stages
            while rain_stage_idx < len(RAIN_STAGES) and \
                  t >= RAIN_STAGES[rain_stage_idx][0]:
                stage_t, speed, edges = RAIN_STAGES[rain_stage_idx]
                for edge in edges:
                    traci.edge.setMaxSpeed(edge, speed)
                print(f"  [t={int(t)}] Rain stage: {edges} -> {speed} m/s")
                rain_stage_idx += 1

            # Apply delivery stop (incident) once vehicle enters network
            if not incident_applied and t >= 240:
                if INCIDENT_VEH in traci.vehicle.getIDList():
                    try:
                        traci.vehicle.setStop(
                            INCIDENT_VEH,
                            INCIDENT_LANE.split("_")[0],  # edge id
                            pos=INCIDENT_POS,
                            laneIndex=int(INCIDENT_LANE.split("_")[-1]),
                            duration=INCIDENT_DUR_S,
                        )
                        print(f"  [t={int(t)}] Incident: scheduled stop for {INCIDENT_VEH} on "
                              f"{INCIDENT_LANE} pos={INCIDENT_POS} for {INCIDENT_DUR_S}s")
                        incident_applied = True
                    except traci.exceptions.TraCIException as exc:
                        print(f"  [t={int(t)}] WARN: Could not apply stop: {exc}")
                        incident_applied = True

            # Log summary every 30 s
            if int(t) % 30 == 0:
                vehs = traci.vehicle.getIDList()
                speeds = [traci.vehicle.getSpeed(v) for v in vehs] if vehs else [0]
                mean_speed = sum(speeds) / len(speeds) if speeds else 0
                halted = sum(1 for s in speeds if s < 0.1)
                summary_rows.append({
                    "t": int(t),
                    "running": len(vehs),
                    "halted": halted,
                    "mean_speed_mps": round(mean_speed, 2),
                })

    except KeyboardInterrupt:
        print("[incident] Interrupted.")
        traci.close()
        write_manifest(run_dir, seed, end_s, run_id, False, "Interrupted by user.")
        return {"run_id": run_id, "complete": False, "summary_rows": summary_rows}

    traci.close()

    write_manifest(run_dir, seed, end_s, run_id, True,
                   f"incident_applied={incident_applied}")

    # Write summary CSV for quick analysis
    if summary_rows:
        import csv, io
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=["t","running","halted","mean_speed_mps"])
        w.writeheader()
        w.writerows(summary_rows)
        (run_dir / "output" / "summary_traci.csv").write_text(buf.getvalue())

    print(f"[incident] Complete. Outputs: {run_dir}/output/")
    return {"run_id": run_id, "complete": True, "summary_rows": summary_rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--end",  type=int, default=2400)
    args = parser.parse_args()

    result = run(args.seed, args.end)
    if not result.get("complete"):
        print("[FAIL]", result.get("notes", "Incomplete run."))
        sys.exit(1)

    rows = result.get("summary_rows", [])
    if rows:
        print("\nt(s)  running  halted  mean_speed(m/s)")
        for r in rows[::4]:   # every 2 min
            print(f"{r['t']:5d}  {r['running']:7d}  {r['halted']:6d}  {r['mean_speed_mps']:10.2f}")


if __name__ == "__main__":
    main()
