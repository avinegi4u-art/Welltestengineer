"""Tests for buckling, connection VME, and MC histogram."""

import math

import pytest

from engine.buckling import (
    buckling_check,
    dawson_paslay_sinusoidal_klbf,
    effective_axial_for_triaxial,
    sinusoidal_buckling_klbf,
)
from engine.connections import connection_limits, iso_ellipse_burst_allowance
from engine.geometry import pipe_id_from_weight
from engine.montecarlo import run_monte_carlo
from engine.ratings import calc_pipe_ratings


def test_effective_axial_adds_bending():
    eff = effective_axial_for_triaxial(100, 7, 30, 2.5)
    assert eff > 100


def test_dawson_paslay_deviated():
    id_ = pipe_id_from_weight(7, 29)
    fs = dawson_paslay_sinusoidal_klbf(7, id_, 45, 10, 0.5, 29)
    assert 0 < fs < 500


def test_euler_buckling_span():
    id_ = pipe_id_from_weight(7, 29)
    f = sinusoidal_buckling_klbf(7, id_, 60, 0)
    assert f > 0
    assert f < float("inf")


def test_buckling_zero_compression():
    ratings = calc_pipe_ratings(7, 29, "N80")
    buck = buckling_check(50, ratings, {"fluidInt": 10, "spanFt": 60}, 5000, {}, {"buckling": 1.25}, [])
    assert buck["util"] == 0


def test_buckling_compression_util():
    ratings = calc_pipe_ratings(7, 29, "N80")
    string = {"fluidInt": 11, "radialClearance": 0.5, "spanFt": 60}
    buck = buckling_check(-200, ratings, string, 8000, {}, {"buckling": 1.25}, [
        {"md": 0, "inc": 55, "azi": 0},
        {"md": 10000, "inc": 55, "azi": 0},
    ])
    assert buck["util"] > 0
    assert buck["mode"] in ("Sinusoidal Buckling", "Helical Buckling")


def test_iso_ellipse_burst():
    pb = iso_ellipse_burst_allowance(10000, 500, 250)
    assert 8000 < pb < 10000


def test_connection_generic_vam_top():
    ratings = calc_pipe_ratings(9.625, 53.5, "L80")
    lim = connection_limits(ratings, "VAM TOP", axial_klbf=100, diff_p=2000)
    assert lim["burst"] < ratings["burst"]
    assert lim["tension"] < ratings["tension"]
    assert lim["vme"]["label"] == "VAM TOP"


def test_connection_manufacturer_vme_curve():
    ratings = calc_pipe_ratings(9.625, 53.5, "L80")
    pipe = {"conn": "VAM TOP", "od": 9.625, "wt": 53.5, "grade": "L80", "vmeCurveId": "VAM_DEMO"}
    curves = {
        "VAM_DEMO": {
            "label": "VAM TOP Demo",
            "points": [
                {"axialKlbf": 0, "burstPsi": 10000},
                {"axialKlbf": 200, "burstPsi": 8500},
                {"axialKlbf": 400, "burstPsi": 6000},
            ],
            "connBurst0": 10000,
            "connTension0": 400,
        }
    }
    lim = connection_limits(ratings, "VAM TOP", axial_klbf=200, diff_p=3000, pipe=pipe, vme_curves=curves)
    assert lim["vme"]["source"] == "manufacturer_csv"
    assert lim["burst"] <= 8500


def test_monte_carlo_histogram():
    payload = {
        "inputs": {
            "ppUncertaintyPct": 5,
            "fgUncertaintyPct": 5,
            "mwUncertaintyPct": 2,
            "analysisStepFt": 4000,
            "sfBuckling": 1.25,
        },
        "state": {
            "catalog": [{"id": "P", "od": 9.625, "wt": 53.5, "grade": "L80", "conn": "BTC"}],
            "strings": [{
                "id": "s1", "label": "Prod", "pipeId": "P", "top": 0, "shoe": 8000,
                "toc": 1000, "fluidInt": 10, "fluidExt": 9, "spanFt": 60,
            }],
            "profiles": [
                {"tvd": 0, "pp": 8.6, "fg": 9.0, "mwInt": 8.6, "mwExt": 8.6, "temp": 70},
                {"tvd": 8000, "pp": 12, "fg": 15, "mwInt": 10, "mwExt": 9, "temp": 180},
            ],
        },
        "scenarios": ["production"],
    }
    result = run_monte_carlo(payload, iterations=60)
    assert result["iterations"] == 60
    assert result["histogram"] is not None
    assert len(result["histogram"]) == 60
    assert result["histogram"] == sorted(result["histogram"])
