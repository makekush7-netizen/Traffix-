import pytest
from eval.compare import compare_results


def result(policy, journey, complete=True):
    return {"run_id": f"run.{policy}", "scenario_id": "rain", "seed": 300, "policy": policy,
            "compliance": 0.6, "sensor_mask_id": "mask", "data_source": "sumo", "cohort_sha256": "same",
            "network_sha256": "net", "incident_sha256": "inc", "complete": complete, "valid": True,
            "mean_journey_s": journey if complete else None, "co2_kg_final": 10 if policy=="fixed" else 8,
            'demand_id':'demand.reference','metric_cohort_sha256':'metric','excluded_vehicle_ids_sha256':'excluded',
            'emission_assumptions_sha256':'emissions','comparison_config_sha256':'bounds','probe_assignment_sha256':'probes'}


def test_reactive_predictive_gain_is_separate_from_fixed_gain():
    report = compare_results([result("fixed",100),result("reactive",80),result("predictive",70)])
    pair = report["pairs"][0]
    assert pair["predictive_vs_fixed_pct"] == pytest.approx(30)
    assert pair["predictive_vs_reactive_pct"] == pytest.approx(12.5)


def test_incomplete_policy_cannot_claim_improvement():
    report = compare_results([result("fixed",100),result("reactive",80),result("predictive",0,False)])
    assert report["pairs"][0]["predictive_vs_fixed_pct"] is None
    assert len(report["invalid_runs"]) == 1


def test_changed_cohort_is_not_a_paired_comparison():
    changed=result("predictive",50)
    changed["cohort_sha256"]="different"
    with pytest.raises(ValueError, match="cohort"):
        compare_results([result("fixed",100),changed])
