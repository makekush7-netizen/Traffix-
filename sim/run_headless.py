"""
sim/run_headless.py — run the bazaar scenario headless and save output.

Usage:
    python sim/run_headless.py [--seed 42] [--end 2400] [--policy fixed]

Produces runs/<run_id>/ with:
    trips.xml, summary.xml, emissions.xml, detectors.xml,
    detectors_truth.xml, manifest.json

AGENTS.md rule 9: never claim improvement without saved run files.
"""

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SIM_ROOT  = Path(__file__).parent
NET_DIR   = SIM_ROOT / "net"
RUNS_DIR  = REPO_ROOT / "runs"


def build_run_id(seed: int, policy: str) -> str:
    ts = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    return f"run.bazaar.seed{seed:03d}.{policy}.{ts}"


def make_run_dir(run_id: str) -> Path:
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "output").mkdir(exist_ok=True)
    return run_dir


def write_manifest(run_dir: Path, args, run_id: str, returncode: int, stderr: str):
    manifest = {
        "run_id":       run_id,
        "seed":         args.seed,
        "policy":       args.policy,
        "end_s":        args.end,
        "sumocfg":      str(NET_DIR / "bazaar.sumocfg"),
        "sumo_version": "Eclipse SUMO 1.28.0",
        "exit_code":    returncode,
        "timestamp":    datetime.datetime.now().isoformat(),
        "complete":     returncode == 0,
        "notes":        stderr[-1000:] if stderr else "",
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


def run_sumo(args, run_dir: Path):
    output_dir = run_dir / "output"

    cmd = [
        "sumo",
        "--seed",            str(args.seed),
        "-c",                str(NET_DIR / "bazaar.sumocfg"),
        "--end",             str(args.end),
        "--no-step-log",
        "--tripinfo-output", str(output_dir / "trips.xml"),
        "--summary-output",  str(output_dir / "summary.xml"),
        "--emission-output", str(output_dir / "emissions.xml"),
    ]

    print(f"[run_headless] {' '.join(cmd)}")
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=str(NET_DIR)
    )
    return result


def collect_detector_output(run_dir: Path):
    """Copy detector output files into run directory if produced."""
    for fname in ("detectors.xml", "detectors_truth.xml"):
        src = NET_DIR / "output" / fname
        dst = run_dir / "output" / fname
        if src.exists():
            shutil.copy2(src, dst)


def main():
    parser = argparse.ArgumentParser(description="Run bazaar scenario headless.")
    parser.add_argument("--seed",   type=int, default=42)
    parser.add_argument("--end",    type=int, default=2400,
                        help="Simulation end time in seconds.")
    parser.add_argument("--policy", choices=["fixed", "reactive", "predictive"],
                        default="fixed",
                        help="Policy label for run ID (does not change SUMO; used for naming).")
    args = parser.parse_args()

    run_id  = build_run_id(args.seed, args.policy)
    run_dir = make_run_dir(run_id)

    print(f"[run_headless] run_id  : {run_id}")
    print(f"[run_headless] run_dir : {run_dir}")

    # Ensure detector output directory exists
    (NET_DIR / "output").mkdir(exist_ok=True)

    result = run_sumo(args, run_dir)

    collect_detector_output(run_dir)
    write_manifest(run_dir, args, run_id, result.returncode, result.stderr)

    if result.returncode != 0:
        print("[FAIL] SUMO exited with errors:")
        print(result.stderr[-3000:])
        sys.exit(1)

    print(f"[OK] Run complete. Outputs in {run_dir}/output/")
    print(f"     manifest: {run_dir}/manifest.json")

    # Print brief summary stats if summary file exists
    summary_path = run_dir / "output" / "summary.xml"
    if summary_path.exists():
        import xml.etree.ElementTree as ET
        tree = ET.parse(summary_path)
        steps = list(tree.getroot())
        if steps:
            last = steps[-1]
            print(f"     Last step t={last.get('time')}s: "
                  f"running={last.get('running')}, "
                  f"waiting={last.get('waiting')}, "
                  f"meanSpeed={last.get('meanSpeed')}")


if __name__ == "__main__":
    main()
