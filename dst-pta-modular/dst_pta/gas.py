"""Gas pseudopressure and pseudotime transforms."""

from __future__ import annotations

import numpy as np


def pseudopressure(pressure_psi: np.ndarray, mu_z_avg: float | np.ndarray) -> np.ndarray:
    """
    Real-gas pseudopressure m(p) = ∫ 2p / (μ Z) dp.
    Screening: use average μZ over range (field units).
    """
    p = np.asarray(pressure_psi, dtype=float)
    if np.isscalar(mu_z_avg):
        return 2.0 * p / max(mu_z_avg, 1e-6)
    return 2.0 * p / np.maximum(mu_z_avg, 1e-6)


def pseudotime(time_hr: np.ndarray, mu_z_avg: float, ct_avg: float) -> np.ndarray:
    """Pseudotime t_a = t / (μ ct)_avg — constant composibility screening."""
    return np.asarray(time_hr, dtype=float) / max(mu_z_avg * ct_avg, 1e-12)


def estimate_muz_from_pvt(pressure_psi: np.ndarray, gamma_g: float = 0.65, t_f: float = 180.0) -> float:
    """Very simplified μZ estimate for screening (not PVT-table grade)."""
    p_avg = float(np.mean(pressure_psi))
    # Lee-Gonzalez-Eakin style rough viscosity + Z ~ 0.9 at moderate pressure
    z = 0.9
    mu = 0.01 * (0.001 * p_avg) ** 0.5 * (1 + 0.001 * gamma_g * t_f)
    return max(mu * z, 0.02)
