"""Engine regression tests."""

import math

import pytest

from engine.geometry import pipe_id_from_weight
from engine.loads import cementing_pressure_at_depth, hydrostatic_psi, surge_swab_margin_ppg, wear_at_depth
from engine.ratings import (
    api_collapse_pressure,
    barlow_burst,
    body_yield_tension_klbf,
    calc_pipe_ratings,
    sour_derating_factor,
    temp_derating_factor,
)
from engine.triaxial import biaxial_burst_factor, triaxial_check


def test_barlow_7_23_n80():
    id_ = pipe_id_from_weight(7, 23)
    got = barlow_burst(7, id_, 80000)
    assert abs(got - 6444) / 6444 < 0.02


def test_hydrostatic_10ppg_10000():
    assert abs(hydrostatic_psi(10, 10000) - 5200) < 1


def test_collapse_7_23_n80():
    id_ = pipe_id_from_weight(7, 23)
    got = api_collapse_pressure(7, id_, 80000)
    assert abs(got - 4402) / 4402 < 0.03


def test_tension_9_625_p110():
    id_ = pipe_id_from_weight(9.625, 53.5)
    got = body_yield_tension_klbf(9.625, id_, 110000)
    assert abs(got - 1513) / 1513 < 0.03


def test_iso_burst_higher_than_api():
    id_ = pipe_id_from_weight(7, 29)
    api = barlow_burst(7, id_, 80000, "api")
    iso = barlow_burst(7, id_, 80000, "iso")
    assert iso > api


def test_sour_derating():
    assert sour_derating_factor(0) == 1.0
    assert sour_derating_factor(0.5) == pytest.approx(0.85, rel=0.01)


def test_temp_derate_p110_400f():
    assert temp_derating_factor("P110", 400) == pytest.approx(0.9, rel=0.02)


def test_wear_at_depth_profile():
    profiles = {"s1": [{"top": 0, "bottom": 5000, "wearPct": 5}, {"top": 5000, "bottom": 10000, "wearPct": 15}]}
    assert wear_at_depth(3000, "s1", 0, profiles, 0) == 5
    assert wear_at_depth(7000, "s1", 0, profiles, 0) == 15


def test_surge_margin_positive():
    m = surge_swab_margin_ppg({"pipeSpeedFtMin": 90, "mudPlasticVisc": 25}, True)
    assert m > 0


def test_swab_margin_negative():
    m = surge_swab_margin_ppg({"pipeSpeedFtMin": 90, "mudPlasticVisc": 25}, False)
    assert m < 0


def test_cementing_schedule_pressure():
    sched = [{"topTvd": 0, "bottomTvd": 8000, "densityPpg": 15.5}]
    p = cementing_pressure_at_depth(5000, sched, 10)
    assert p > hydrostatic_psi(10, 5000)


def test_biaxial_burst_compression():
    id_ = pipe_id_from_weight(7, 29)
    f = biaxial_burst_factor(-200, 80000, 7, id_)
    assert abs(f - 0.789) / 0.789 < 0.03


def test_triaxial_burst_dominated():
    r = calc_pipe_ratings(7, 29, "N80")
    tri = triaxial_check(50, 4000, 1000, r, {"burst": 1.1, "collapse": 1, "tension": 1.2, "triaxial": 1.25})
    assert 0.3 < tri["burst_util"] < 0.5


def test_wear_reduces_burst():
    pristine = calc_pipe_ratings(7, 29, "N80", wear_pct=0)
    worn = calc_pipe_ratings(7, 29, "N80", wear_pct=10)
    assert pristine["burst"] > worn["burst"]


def test_pipe_id_formula():
    assert abs(pipe_id_from_weight(7, 29) - 6.176) / 6.176 < 0.01
