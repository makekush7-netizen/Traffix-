"""
tests/test_sim_validate.py — Acceptance test for sim environment.
Runs all validation checks from sim.validate.
"""
from sim.validate import (
    check_files,
    check_registry,
    check_demand,
    check_detector_isolation,
    check_sumo_headless,
)


def test_sim_files_exist():
    check_files()


def test_sim_registry():
    check_registry()


def test_sim_demand():
    check_demand()


def test_sim_detector_isolation():
    check_detector_isolation()


def test_sim_sumo_headless():
    check_sumo_headless(n_steps=10)
