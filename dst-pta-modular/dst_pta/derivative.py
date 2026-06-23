"""Bourdet pressure derivative and diagnostic plotting helpers."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class DerivativeResult:
    dt_hr: np.ndarray
    delta_p_psi: np.ndarray
    derivative_psi_per_hr: np.ndarray
    log_dt: np.ndarray
    log_derivative: np.ndarray
    bourdet_l: float
    notes: str


def bourdet_derivative(
    dt_hr: np.ndarray,
    delta_p_psi: np.ndarray,
    L: float = 0.15,
) -> np.ndarray:
    """
    Bourdet et al. (1989) pressure derivative on log-time grid.
    L is smoothing parameter (fraction of log-time window, typically 0.1–0.3).
    """
    n = len(dt_hr)
    if n < 3:
        return np.full(n, np.nan)

    dt = np.maximum(dt_hr, 1e-10)
    log_t = np.log(dt)
    deriv = np.full(n, np.nan)

    for i in range(1, n - 1):
        # Expand left/right in ln(t) until separation reaches L (Bourdet window)
        li = i - 1
        while li > 0 and (log_t[i] - log_t[li]) < L:
            li -= 1
        ri = i + 1
        while ri < n - 1 and (log_t[ri] - log_t[i]) < L:
            ri += 1
        if li >= i or ri <= i:
            continue
        dpl = delta_p_psi[i] - delta_p_psi[li]
        dpr = delta_p_psi[ri] - delta_p_psi[i]
        dtl = log_t[i] - log_t[li]
        dtr = log_t[ri] - log_t[i]
        if dtl <= 0 or dtr <= 0:
            continue
        # Bourdet blend: Δp' = dΔp / d ln(t) = t · dΔp/dt (log-log diagnostic derivative)
        deriv[i] = (dpl / dtl * dtr + dpr / dtr * dtl) / (dtl + dtr)

    # End points: one-sided
    deriv[0] = deriv[1] if n > 1 else np.nan
    deriv[-1] = deriv[-2] if n > 1 else np.nan
    return deriv


def compute_derivative(
    dt_hr: np.ndarray,
    delta_p_psi: np.ndarray,
    bourdet_l: float = 0.15,
) -> DerivativeResult:
    dt = np.maximum(dt_hr, 1e-10)
    deriv = bourdet_derivative(dt, delta_p_psi, L=bourdet_l)
    mask = deriv > 0
    return DerivativeResult(
        dt_hr=dt,
        delta_p_psi=delta_p_psi,
        derivative_psi_per_hr=deriv,
        log_dt=np.log10(dt),
        log_derivative=np.where(mask, np.log10(deriv), np.nan),
        bourdet_l=bourdet_l,
        notes=f"Bourdet derivative with L={bourdet_l:.2f} (log-time smoothing fraction).",
    )


def reference_slopes(dt_hr: np.ndarray, anchor_dt: float, anchor_deriv: float) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """
    Reference derivative slopes on log-log plot for regime identification.
    +1: wellbore storage, 0: radial, -1/2: linear flow.
    """
    dt = np.maximum(dt_hr, 1e-10)
    scales = {
        "storage (+1)": 1.0,
        "radial (0)": 0.0,
        "linear (-1/2)": -0.5,
        "boundary (+1 late)": 1.0,
    }
    out = {}
    for name, exp in scales.items():
        if name == "boundary (+1 late)":
            y = anchor_deriv * (dt / anchor_dt) ** exp
            y = np.where(dt >= anchor_dt * 3, y, np.nan)
        else:
            y = anchor_deriv * (dt / anchor_dt) ** exp
        out[name] = (dt, y)
    return out
