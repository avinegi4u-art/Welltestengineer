"""Agarwal equivalent time and superposition for multi-rate DST buildups."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .data_loader import DSTCycle, PressureSeries, ReservoirProperties


@dataclass
class SuperpositionResult:
    dt_hr: np.ndarray
    delta_p_psi: np.ndarray
    horner_ratio: np.ndarray
    equivalent_time_hr: np.ndarray
    tp_hr: float
    q_ref_bpd: float
    notes: str


def cumulative_rate_time(flow_times_hr: np.ndarray, flow_rates_bpd: np.ndarray) -> float:
    """Total rate-time (rate-hours) prior to shut-in."""
    if len(flow_times_hr) < 2:
        return float(flow_rates_bpd[0] * flow_times_hr[-1]) if len(flow_times_hr) else 0.0
    dt = np.diff(flow_times_hr, prepend=flow_times_hr[0])
    return float(np.sum(flow_rates_bpd * dt))


def agarwal_equivalent_time(tp_hr: float, dt_hr: np.ndarray) -> np.ndarray:
    """
    Agarwal equivalent time for buildup: te = tp + dt (oilfield convention for Horner).
    For log-time derivative plots we use shut-in elapsed dt.
    """
    dt = np.maximum(dt_hr, 1e-8)
    return tp_hr + dt


def horner_superposition_ratio(tp_hr: float, dt_hr: np.ndarray) -> np.ndarray:
    """Horner time ratio (tp + Δt) / Δt used for semi-log straight-line analysis."""
    dt = np.maximum(dt_hr, 1e-8)
    return (tp_hr + dt) / dt


def equivalent_producing_time(cycles: list[DSTCycle], buildup_start_hr: float) -> float:
    """Sum producing rate-time from flow cycles before buildup onset."""
    total = 0.0
    for cycle in cycles:
        if cycle.kind != "flow" or cycle.end_hr > buildup_start_hr:
            continue
        total += cycle.avg_rate_bpd * cycle.duration_hr
    q_last = next((c.q_ref_bpd for c in reversed(cycles) if c.kind == "flow"), 1.0)
    return total / max(q_last, 1e-6)


def apply_superposition_to_buildup(
    buildup: PressureSeries,
    full_series: PressureSeries | None = None,
    tp_hr: float | None = None,
    q_ref: float | None = None,
) -> SuperpositionResult:
    """
    Prepare buildup for Horner / derivative analysis with superposition time bases.
    tp: equivalent producing time before shut-in (hr).
    """
    props = buildup.properties
    t = buildup.time_hr
    p = buildup.pressure_psi
    dt = np.maximum(t - t[0], 1e-8)
    p0 = p[0]
    delta_p = p - p0

    if full_series and full_series.cycles:
        abs_start = buildup.origin_time_hr if buildup.origin_time_hr > 0 else float(buildup.time_hr[0])
        tp = tp_hr if tp_hr is not None else equivalent_producing_time(full_series.cycles, abs_start)
        q = q_ref if q_ref is not None else props.q
        last_flow = next((c for c in reversed(full_series.cycles) if c.kind == "flow"), None)
        if last_flow:
            q = last_flow.q_ref_bpd
    else:
        tp = tp_hr if tp_hr is not None else props.tp
        q = q_ref if q_ref is not None else props.q

    te = agarwal_equivalent_time(tp, dt)
    horner = horner_superposition_ratio(tp, dt)
    notes = (
        f"Superposition: tp={tp:.3f} hr, q_ref={q:.1f} bpd. "
        f"Agarwal te = tp + Δt; Horner ratio (tp+Δt)/Δt for semi-log fit."
    )
    return SuperpositionResult(
        dt_hr=dt,
        delta_p_psi=delta_p,
        horner_ratio=horner,
        equivalent_time_hr=te,
        tp_hr=float(tp),
        q_ref_bpd=float(q),
        notes=notes,
    )


def multi_rate_kernel_correction(
    time_hr: np.ndarray,
    pressure_psi: np.ndarray,
    rate_steps: list[tuple[float, float, float]],
) -> np.ndarray:
    """
  Simplified superposition kernel for variable-rate history.
  rate_steps: list of (start_hr, end_hr, rate_bpd).
  Returns approximate deconvolved pressure buildup contribution.
    """
    p = pressure_psi.copy()
    kernel = np.ones_like(time_hr)
    for start, end, q in rate_steps:
        if abs(q) < 1e-6:
            continue
        mask = (time_hr >= start) & (time_hr <= end)
        dt = np.maximum(time_hr[mask] - start, 1e-6)
        kernel[mask] += 0.15 * q / max(q, 1.0) * np.log10(dt + 1)
    return p / np.maximum(kernel, 0.2)
