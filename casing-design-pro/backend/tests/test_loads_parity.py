"""Parity tests for axial and pressure load models."""

import copy

import pytest

from engine.analyzer import run_analysis
from engine.loads import (
    axial_force_at_depth,
    column_pressure_psi,
    external_pressure_at_depth,
    external_zone,
    hydrostatic_psi,
    internal_pressure_at_depth,
    offshore_external_psi,
    temperature_at_depth,
)


DEMO_STATE = {
    "catalog": [
        {"id": "P", "od": 9.625, "wt": 53.5, "grade": "L80", "conn": "VAM TOP", "wearPct": 8},
    ],
    "strings": [
        {
            "id": "s3",
            "label": "Production",
            "type": "production",
            "top": 0,
            "shoe": 11000,
            "toc": 2000,
            "pipeId": "P",
            "fluidInt": 11.5,
            "fluidExt": 9.5,
            "hangOffKlbf": 0,
            "preTensionKlbf": 0,
            "hangerLoadKlbf": 25,
            "apbSealed": True,
            "apbPsi": 1800,
        }
    ],
    "profiles": [
        {"tvd": 0, "pp": 8.6, "fg": 9.0, "mwInt": 8.6, "mwExt": 8.6, "temp": 70},
        {"tvd": 11000, "pp": 11.5, "fg": 15.0, "mwInt": 11.5, "mwExt": 9.5, "temp": 220},
    ],
    "cementingSchedule": [{"topTvd": 0, "bottomTvd": 11000, "densityPpg": 15.2}],
    "thermal": {
        "enabled": True,
        "mode": "production",
        "circulatingTempF": 120,
        "productionTempF": 285,
        "relaxDepthFt": 5000,
    },
    "packers": [
        {"id": "pk1", "stringId": "s3", "depth": 10800, "setDownKlbf": 35, "annulusPsi": 1200, "sealIdIn": 4.25}
    ],
    "annuli": [
        {
            "id": "a1",
            "innerStringId": "s3",
            "outerStringId": "s2",
            "topTvd": 2000,
            "bottomTvd": 10800,
            "initialPressurePsi": 1200,
            "initialTempF": 70,
            "volumeBbl": 85,
            "complianceBblPerPsi": 0.02,
            "fluidExpPerF": 0.00045,
            "sealed": True,
        }
    ],
}

DEMO_INP = {
    "analysisStepFt": 1000,
    "designCode": "api",
    "refTempF": 70,
    "thermalEnabled": True,
    "apbEnabled": True,
    "apbDefaultPsi": 500,
    "waterDepth": 0,
    "sfBurst": 1.1,
    "sfCollapse": 1.0,
    "sfTension": 1.2,
    "sfTriaxial": 1.25,
}


def _string():
    return DEMO_STATE["strings"][0]


def test_offshore_external_onshore():
    p = offshore_external_psi(5000, 9.5, {"waterDepth": 0})
    assert abs(p - hydrostatic_psi(9.5, 5000)) < 1


def test_offshore_external_subsea():
    inp = {"waterDepth": 1000, "rigElev": 100, "seawaterPpg": 8.6}
    p = offshore_external_psi(5000, 9.5, inp)
    mudline = 1100
    expected = hydrostatic_psi(8.6, mudline) + hydrostatic_psi(9.5, 5000 - mudline)
    assert abs(p - expected) < 2


def test_external_zone_open_vs_cemented():
    s = _string()
    assert external_zone(1000, s) == "open"
    assert external_zone(5000, s) == "cemented"


def test_production_external_cemented():
    inp = {**DEMO_INP, "apbEnabled": False}
    state = {**DEMO_STATE, "annuli": []}
    p = external_pressure_at_depth(5000, _string(), "production", inp, state["profiles"], state)
    pp = 8.6 + (11.5 - 8.6) * (5000 / 11000)
    expected = hydrostatic_psi(pp, 5000) * 0.65
    assert abs(p - expected) < 50


def test_internal_production_max_mw_pp():
    p = internal_pressure_at_depth(
        5000, _string(), "production", DEMO_INP, DEMO_STATE["profiles"], DEMO_STATE, []
    )
    mw = hydrostatic_psi(11.5, 5000)
    pp = hydrostatic_psi(8.6 + (11.5 - 8.6) * (5000 / 11000), 5000) * 0.95
    assert abs(p - max(mw, pp)) < 5


def test_internal_cementing_schedule():
    p = internal_pressure_at_depth(
        5000, _string(), "cementing", DEMO_INP, DEMO_STATE["profiles"], DEMO_STATE, DEMO_STATE["cementingSchedule"]
    )
    assert p > hydrostatic_psi(11.5, 5000)


def test_column_pressure_fluid_segments():
    state = copy.deepcopy(DEMO_STATE)
    state["fluidSegments"] = {
        "s3": [
            {"top": 0, "bottom": 5000, "ppg": 8.6},
            {"top": 5000, "bottom": 11000, "ppg": 12.0},
        ]
    }
    p = column_pressure_psi(7000, _string(), state["profiles"], state)
    expected = hydrostatic_psi(8.6, 5000) + hydrostatic_psi(12.0, 2000)
    assert abs(p - expected) < 2


def test_axial_buoyed_weight_positive():
    catalog = {p["id"]: p for p in DEMO_STATE["catalog"]}
    axial = axial_force_at_depth(
        5000, _string(), DEMO_INP, DEMO_STATE, DEMO_STATE["profiles"], [], "production", catalog
    )
    assert axial > 40


def test_axial_hanger_load_near_surface():
    catalog = {p["id"]: p for p in DEMO_STATE["catalog"]}
    axial_top = axial_force_at_depth(
        50, _string(), DEMO_INP, DEMO_STATE, DEMO_STATE["profiles"], [], "production", catalog
    )
    axial_deep = axial_force_at_depth(
        5000, _string(), DEMO_INP, DEMO_STATE, DEMO_STATE["profiles"], [], "production", catalog
    )
    assert axial_top > axial_deep


def test_temperature_production_mode():
    t = temperature_at_depth(8000, DEMO_INP, DEMO_STATE, "thermalProduction")
    assert 150 < t < 280


def test_run_analysis_returns_loads_and_rows():
    result = run_analysis({"inputs": DEMO_INP, "state": DEMO_STATE})
    assert result["check_count"] > 0
    assert result["max_util"] > 0
    assert result["governing"] is not None
    assert result["engine"] == "python"
    assert len(result["loads"]) == len(result["rows"])
    row = result["rows"][0]
    assert "p_int" in row
    assert "axial_klbf" in row
    assert row["axial_klbf"] > 0


def test_run_analysis_no_placeholder_axial():
    """Axial should reflect real buoyed weight, not MW-based placeholder."""
    result = run_analysis({"inputs": {**DEMO_INP, "analysisStepFt": 5500}, "state": DEMO_STATE, "scenarios": ["production"]})
    axials = [r["axial_klbf"] for r in result["rows"]]
    assert max(axials) > 100
    assert min(axials) < max(axials)
