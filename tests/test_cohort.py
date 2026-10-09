import pytest
from eval.cohort import Trip, summarize_cohort, integrate_co2


def trip(vid, scheduled, departed, arrived, status="arrived", co2=1000000):
    return Trip(vid, scheduled, departed, arrived, status, waiting_s=5, co2_mg=co2)


def test_counts_entry_wait_and_detour_in_mean_journey():
    result = summarize_cohort([trip("a", 0, 20, 100), trip("b", 10, 10, 150)])
    assert result["mean_journey_s"] == 120
    assert result["co2_kg_final"] == 2
    assert result["scheduled"] == result["arrived"] == 2


def test_unfinished_trip_blocks_completed_only_headline():
    result = summarize_cohort([trip("a", 0, 0, 10), trip("b", 0, None, None, "pending")])
    assert result["complete"] is False
    assert result["mean_journey_s"] is None
    assert result["co2_kg_final"] is None
    assert result["pending"] == 1


def test_duplicate_vehicle_and_impossible_times_are_errors():
    with pytest.raises(ValueError):
        summarize_cohort([trip("a", 0, 0, 10), trip("a", 0, 0, 10)])
    with pytest.raises(ValueError):
        trip("a", 20, 10, 30)


def test_removed_trip_cannot_count_as_completed():
    result = summarize_cohort([trip("a", 0, 0, None, "removed")])
    assert result["removed"] == 1
    assert result["complete"] is False


def test_teleport_invalidates_traffic_savings():
    result = summarize_cohort([trip("a", 0, 0, 10)], teleported=1)
    assert result["valid"] is False


def test_emission_rate_is_integrated_over_simulated_step():
    assert integrate_co2([1000, 2000], step_s=2) == pytest.approx(0.006)
    with pytest.raises(ValueError):
        integrate_co2([-1], step_s=1)
