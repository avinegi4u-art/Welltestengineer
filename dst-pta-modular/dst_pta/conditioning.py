"""Noise filtering, outlier rejection, and pressure conditioning."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import median_filter

from .data_loader import PressureSeries


def moving_median(y: np.ndarray, window: int = 5) -> np.ndarray:
    if window < 3:
        return y.copy()
    size = window if window % 2 == 1 else window + 1
    return median_filter(y, size=size, mode="nearest")


def mad_outlier_mask(y: np.ndarray, threshold: float = 4.5) -> np.ndarray:
    """Return True where points are outliers (median absolute deviation)."""
    med = np.median(y)
    mad = np.median(np.abs(y - med)) or 1.0
    z = 0.6745 * (y - med) / mad
    return np.abs(z) > threshold


def remove_outliers(time_hr: np.ndarray, pressure_psi: np.ndarray, threshold: float = 4.5):
    mask = ~mad_outlier_mask(pressure_psi, threshold)
    return time_hr[mask], pressure_psi[mask], int(np.sum(~mask))


def condition_series(
    series: PressureSeries,
    median_window: int = 5,
    outlier_threshold: float = 4.5,
    apply_median: bool = True,
) -> tuple[PressureSeries, dict]:
    """
    Filter noise and remove spikes. Returns conditioned series and QC summary.
    """
    t = series.time_hr.copy()
    p = series.pressure_psi.copy()
    n_removed = 0
    if outlier_threshold > 0:
        t, p, n_removed = remove_outliers(t, p, outlier_threshold)
    if apply_median and len(p) >= median_window:
        p = moving_median(p, median_window)
    rate = None
    if series.rate_bpd is not None and len(series.rate_bpd) == len(series.time_hr):
        # Align rate to surviving points by nearest time
        rate_full = series.rate_bpd
        rate = np.array([rate_full[np.argmin(np.abs(series.time_hr - ti))] for ti in t])

    conditioned = PressureSeries(
        time_hr=t,
        pressure_psi=p,
        rate_bpd=rate,
        source=series.source + " (conditioned)",
        properties=series.properties,
    )
    qc = {
        "points_in": series.n,
        "points_out": len(t),
        "outliers_removed": n_removed,
        "median_window": median_window if apply_median else 0,
    }
    return conditioned, qc
