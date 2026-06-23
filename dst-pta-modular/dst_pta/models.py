"""Analytical type curves and auto-fit (least squares on log derivative)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np
from scipy.optimize import minimize


class ModelType(str, Enum):
    RADIAL = "infinite_acting_radial"
    SEALING_FAULT = "sealing_fault"
    CONSTANT_PRESSURE = "constant_pressure_boundary"
    DUAL_POROSITY = "dual_porosity"


@dataclass
class TypeCurveParams:
    k_md: float
    skin: float
    cd: float = 100.0
    omega: float = 0.1
    lambda_dp: float = 1e-6
    distance_ft: float = 500.0


@dataclass
class TypeCurveFit:
    model: ModelType
    params: TypeCurveParams
    rmse_log: float
    shift_log_t: float = 0.0
    shift_log_p: float = 0.0


def dimensionless_time(t_hr: float, k_md: float, phi: float, mu_cp: float, ct_1psi: float, rw_ft: float) -> float:
    denom = phi * mu_cp * ct_1psi * rw_ft ** 2
    return 0.0002637 * k_md * t_hr / max(denom, 1e-20)


def dimensionless_pressure_derivative_radial(tD: np.ndarray, cd: float, skin: float) -> np.ndarray:
    """Simplified WBS + radial late-time derivative plateau (screening grade)."""
    tD = np.maximum(tD, 1e-12)
    cd = max(cd, 1e-6)
    storage = tD / cd
    radial = 0.5 * np.ones_like(tD)
    x = np.log10(np.maximum(tD / cd, 1e-12))
    blend = np.clip((x - 0.1) / 1.2, 0, 1)
    return storage * (1 - blend) + radial * blend


def dual_porosity_derivative(tD: np.ndarray, omega: float, lam: float) -> np.ndarray:
    """Warren-Root style trough on derivative (screening)."""
    base = dimensionless_pressure_derivative_radial(tD, cd=500, skin=0)
    trough = 1.0 - omega * np.exp(-lam * tD * 1e4)
    return base * np.maximum(trough, 0.35)


def fault_derivative(tD: np.ndarray, skin: float, distance_ratio: float = 10.0) -> np.ndarray:
    """Late-time doubling of slope for sealing fault (approximate)."""
    base = dimensionless_pressure_derivative_radial(tD, cd=200, skin=skin)
    late = tD > distance_ratio
    base = base.copy()
    base[late] *= 1.0 + 0.5 * np.log10(np.maximum(tD[late] / distance_ratio, 1))
    return base


def model_derivative(
    model: ModelType,
    dt_hr: np.ndarray,
    params: TypeCurveParams,
    props,
) -> np.ndarray:
    """Convert dimensionless derivative to field derivative (psi/hr) scale."""
    tD = np.array([dimensionless_time(t, params.k_md, props.phi, props.mu, props.ct, props.rw) for t in dt_hr])
    if model == ModelType.RADIAL:
        pDder = dimensionless_pressure_derivative_radial(tD, params.cd, params.skin)
    elif model == ModelType.SEALING_FAULT:
        pDder = fault_derivative(tD, params.skin)
    elif model == ModelType.CONSTANT_PRESSURE:
        pDder = dimensionless_pressure_derivative_radial(tD, params.cd, params.skin) * 0.85
        late = tD > 50
        pDder[late] *= 0.6
    elif model == ModelType.DUAL_POROSITY:
        pDder = dual_porosity_derivative(tD, params.omega, params.lambda_dp)
    else:
        pDder = dimensionless_pressure_derivative_radial(tD, params.cd, params.skin)

    # Field scaling: Δp' ≈ (141.2 q B μ / (k h)) * pD'
    scale = 141.2 * props.q * props.b * props.mu / max(params.k_md * props.h, 1e-6)
    return pDder * scale / np.maximum(dt_hr, 1e-6) * dt_hr  # approximate Bourdet units


def auto_fit_derivative(
    dt_hr: np.ndarray,
    obs_deriv: np.ndarray,
    props,
    model: ModelType = ModelType.RADIAL,
    k0: float = 10.0,
    skin0: float = 0.0,
) -> TypeCurveFit:
    """Least-squares fit in log-log derivative space."""
    mask = np.isfinite(obs_deriv) & (obs_deriv > 0) & (dt_hr > 0)
    if np.sum(mask) < 4:
        return TypeCurveFit(model, TypeCurveParams(k0, skin0), rmse_log=9.9)

    dt = dt_hr[mask]
    y_obs = np.log10(obs_deriv[mask])

    def objective(x):
        k, s = max(x[0], 0.01), x[1]
        p = TypeCurveParams(k_md=k, skin=s)
        y_mod = np.log10(np.maximum(model_derivative(model, dt, p, props), 1e-12))
        return float(np.mean((y_obs - y_mod) ** 2))

    res = minimize(objective, x0=[k0, skin0], bounds=[(0.01, 5000), (-10, 50)], method="L-BFGS-B")
    k_fit, s_fit = res.x
    rmse = float(np.sqrt(res.fun))
    return TypeCurveFit(model, TypeCurveParams(k_md=float(k_fit), skin=float(s_fit)), rmse_log=rmse)
