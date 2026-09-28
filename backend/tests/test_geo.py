"""Geo maths tests (section 14.1), including the wind from/toward trap."""
import pytest

from app.geo import angular_diff, bearing_deg, haversine_km, wind_toward_deg


def test_haversine_delhi_mumbai():
    d = haversine_km(28.6139, 77.2090, 19.0760, 72.8777)
    assert 1125 <= d <= 1175  # about 1150 km, tolerance 25


def test_haversine_zero():
    assert haversine_km(28.0, 77.0, 28.0, 77.0) == pytest.approx(0.0, abs=1e-9)


def test_bearing_north_and_east():
    # Due north: same longitude, target above.
    assert bearing_deg(10.0, 77.0, 20.0, 77.0) == pytest.approx(0.0, abs=0.5)
    # Due east along the equator.
    assert bearing_deg(0.0, 77.0, 0.0, 87.0) == pytest.approx(90.0, abs=0.5)


def test_bearing_range():
    b = bearing_deg(28.6, 77.2, 19.07, 72.87)
    assert 0.0 <= b < 360.0


def test_angular_diff_wraparound():
    assert angular_diff(350.0, 10.0) == pytest.approx(20.0, abs=1e-9)
    assert angular_diff(10.0, 350.0) == pytest.approx(20.0, abs=1e-9)
    assert angular_diff(0.0, 180.0) == pytest.approx(180.0, abs=1e-9)


def test_wind_toward_is_from_plus_180():
    # The classic mix-up: wind_dir is where wind comes FROM (section 8).
    assert wind_toward_deg(0.0) == pytest.approx(180.0)
    assert wind_toward_deg(315.0) == pytest.approx(135.0)
    assert wind_toward_deg(270.0) == pytest.approx(90.0)
    assert wind_toward_deg(350.0) == pytest.approx(170.0)
