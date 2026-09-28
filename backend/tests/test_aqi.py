"""AQI breakpoint tests (section 14.2)."""
import pytest

from app.services.aqi import category, compute_aqi, pm10_sub_index, pm25_sub_index


def test_pm25_45_is_about_75():
    assert pm25_sub_index(45) == pytest.approx(75.0, abs=0.5)


def test_pm25_300_above_400():
    assert pm25_sub_index(300) > 400


def test_pm25_above_top_band_clamps_to_500():
    assert pm25_sub_index(500) == 500.0


def test_pm10_500_clamps():
    assert pm10_sub_index(500) == 500.0


def test_pm10_band_edges():
    assert pm10_sub_index(0) == 0.0
    assert pm10_sub_index(50) == pytest.approx(50.0, abs=0.5)
    assert pm10_sub_index(100) == pytest.approx(100.0, abs=0.5)
    assert pm10_sub_index(250) == pytest.approx(200.0, abs=0.5)
    assert pm10_sub_index(350) == pytest.approx(300.0, abs=0.5)
    assert pm10_sub_index(430) == pytest.approx(400.0, abs=0.5)


def test_overall_aqi_is_max_of_subindices():
    aqi = compute_aqi(30, 250)  # pm25 -> 50, pm10 -> 200
    assert aqi == pytest.approx(200.0, abs=0.5)


def test_overall_aqi_none_when_no_pollutants():
    assert compute_aqi(None, None) is None


def test_categories():
    assert category(0) == "Good"
    assert category(50) == "Good"
    assert category(51) == "Satisfactory"
    assert category(150) == "Moderate"
    assert category(250) == "Poor"
    assert category(350) == "Very Poor"
    assert category(450) == "Severe"
