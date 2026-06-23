"""Core PTA calculation tests."""

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dst_pta.conditioning import condition_series
from dst_pta.data_loader import ReservoirProperties, attach_properties, detect_cycles, load_csv
from dst_pta.derivative import bourdet_derivative, compute_derivative
from dst_pta.interpretation import interpret_dst_workflow
from dst_pta.superposition import apply_superposition_to_buildup, horner_superposition_ratio


def test_horner_ratio():
    tp, dt = 4.0, np.array([0.1, 1.0, 10.0])
    h = horner_superposition_ratio(tp, dt)
    assert h[0] > h[-1]
    assert np.isfinite(h).all()


def test_bourdet_positive():
    dt = np.logspace(-2, 1, 40)
    dp = 100 * np.log(dt / 0.01 + 1)
    d = bourdet_derivative(dt, dp, L=0.15)
    assert np.nanmean(d[5:-5]) > 0


def test_demo_workflow():
    sample = ROOT / "sample_data" / "dst_demo.csv"
    series = load_csv(sample)
    props = ReservoirProperties(q=380, tp=4.0, pwf=7780)
    attach_properties(series, props)
    conditioned, qc = condition_series(series, median_window=3, outlier_threshold=5)
    detect_cycles(conditioned)
    results = interpret_dst_workflow(conditioned)
    assert qc["points_out"] >= 10
    assert len(conditioned.cycles) >= 2
    assert len(results) >= 1
    h = results[0].horner
    assert h is not None
    assert h.permeability_md > 0
    assert 0 <= h.r2 <= 1


if __name__ == "__main__":
    test_horner_ratio()
    test_bourdet_positive()
    test_demo_workflow()
    print("All tests passed.")
