"""Tests for VME curves and Monte Carlo."""

import pytest

from engine.montecarlo import percentile, perturb_profiles, run_monte_carlo
from engine.vme import (
    connection_limits_from_curve,
    curve_envelope,
    interpolate_burst_at_axial,
    parse_vme_csv_rows,
)


SAMPLE_CURVE = {
    "id": "VAM_TOP_9625",
    "label": "VAM TOP 9.625 L80",
    "points": [
        {"axial_klbf": 0, "burst_psi": 10000},
        {"axial_klbf": 200, "burst_psi": 8500},
        {"axial_klbf": 400, "burst_psi": 6000},
        {"axial_klbf": 550, "burst_psi": 2000},
    ],
    "conn_burst0": 10000,
    "conn_tension0": 550,
}


def test_curve_envelope():
    env = curve_envelope(SAMPLE_CURVE["points"])
    assert env["conn_burst0"] == 10000
    assert env["conn_tension0"] == 550


def test_interpolate_burst_midpoint():
    got = interpolate_burst_at_axial(SAMPLE_CURVE["points"], 200)
    assert got == pytest.approx(8500, rel=0.01)


def test_interpolate_burst_between_points():
    got = interpolate_burst_at_axial(SAMPLE_CURVE["points"], 100)
    assert 8500 < got < 10000


def test_connection_limits_from_curve():
    ratings = {"burst": 11000, "collapse": 8000, "tension": 600, "compression": 600}
    lim = connection_limits_from_curve(ratings, SAMPLE_CURVE, axial_klbf=200, diff_p=3000)
    assert lim["burst"] == pytest.approx(8500, rel=0.01)
    assert lim["vme"]["source"] == "manufacturer_csv"


def test_parse_vme_csv():
    rows = [
        ["connection", "axial_klbf", "burst_psi"],
        ["VAM TOP", "0", "10000"],
        ["VAM TOP", "200", "8500"],
    ]
    curves = parse_vme_csv_rows(rows)
    assert len(curves) == 1
    assert len(curves[0]["points"]) == 2
    assert curves[0]["conn_burst0"] == 10000


def test_percentile():
    vals = list(range(1, 101))
    assert percentile(vals, 50) == pytest.approx(50.5, rel=0.02)
    assert percentile(vals, 90) == pytest.approx(90.1, rel=0.02)


def test_perturb_profiles_spread():
    profiles = [{"tvd": 0, "pp": 10, "fg": 12, "mwInt": 9, "mwExt": 9}]
    samples = [perturb_profiles(profiles, {"ppUncertaintyPct": 10, "fgUncertaintyPct": 10, "mwUncertaintyPct": 2})[0]["pp"] for _ in range(100)]
    assert max(samples) > 10
    assert min(samples) < 10


def test_monte_carlo_runs():
    payload = {
        "inputs": {"ppUncertaintyPct": 5, "fgUncertaintyPct": 5, "mwUncertaintyPct": 2, "analysisStepFt": 2000},
        "state": {
            "catalog": [{"id": "P", "od": 9.625, "wt": 53.5, "grade": "L80", "conn": "BTC"}],
            "strings": [{"id": "s1", "label": "Prod", "pipeId": "P", "top": 0, "shoe": 8000, "toc": 1000, "fluidInt": 10, "fluidExt": 9}],
            "profiles": [
                {"tvd": 0, "pp": 8.6, "fg": 9.0, "mwInt": 8.6, "mwExt": 8.6, "temp": 70},
                {"tvd": 8000, "pp": 12, "fg": 15, "mwInt": 10, "mwExt": 9, "temp": 180},
            ],
        },
    }
    result = run_monte_carlo(payload, iterations=80)
    assert result["iterations"] == 80
    assert 0 <= result["p50"] <= result["p90"]
    assert 0 <= result["pass_probability"] <= 1
