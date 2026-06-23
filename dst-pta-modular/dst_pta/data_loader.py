"""Load and structure DST pressure / rate time series."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass
class ReservoirProperties:
    """Oilfield units: q bpd, B rb/STB, μ cp, h ft, φ fraction, ct 1/psi, rw ft."""

    q: float = 500.0
    b: float = 1.2
    mu: float = 1.0
    h: float = 50.0
    phi: float = 0.18
    ct: float = 1.2e-5
    rw: float = 0.328
    tp: float = 10.0
    pwf: float = 3000.0
    is_gas: bool = False
    # Gas PVT (optional)
    gamma_g: float = 0.65
    t_res_f: float = 180.0


@dataclass
class DSTCycle:
    """One flow + optional buildup segment."""

    cycle_id: int
    kind: str  # flow | shut-in
    start_idx: int
    end_idx: int
    start_hr: float
    end_hr: float
    duration_hr: float
    avg_rate_bpd: float
    q_ref_bpd: float


@dataclass
class PressureSeries:
    time_hr: np.ndarray
    pressure_psi: np.ndarray
    rate_bpd: np.ndarray | None = None
    source: str = ""
    cycles: list[DSTCycle] = field(default_factory=list)
    properties: ReservoirProperties = field(default_factory=ReservoirProperties)
    origin_time_hr: float = 0.0  # absolute clock time of series start (for split buildups)

    @property
    def n(self) -> int:
        return len(self.time_hr)


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename = {}
    for col in df.columns:
        key = str(col).strip().lower().replace(" ", "_")
        if key in ("time", "t", "time_hr", "dt_hr", "elapsed_hr", "hours"):
            rename[col] = "time_hr"
        elif key in ("pressure", "p", "bhp", "bhp_psi", "pressure_psi"):
            rename[col] = "pressure_psi"
        elif key in ("rate", "q", "rate_bpd", "oil_rate", "liquid_rate"):
            rename[col] = "rate_bpd"
    return df.rename(columns=rename)


def load_csv(path: str | Path) -> PressureSeries:
    """Load CSV with time_hr, pressure_psi and optional rate_bpd."""
    df = pd.read_csv(path)
    df = _normalize_columns(df)
    if "time_hr" not in df.columns or "pressure_psi" not in df.columns:
        raise ValueError("CSV must include time and pressure columns (time_hr, pressure_psi).")
    df = df.dropna(subset=["time_hr", "pressure_psi"]).sort_values("time_hr")
    rate = df["rate_bpd"].to_numpy(dtype=float) if "rate_bpd" in df.columns else None
    return PressureSeries(
        time_hr=df["time_hr"].to_numpy(dtype=float),
        pressure_psi=df["pressure_psi"].to_numpy(dtype=float),
        rate_bpd=rate,
        source=str(path),
    )


def load_dataframe(df: pd.DataFrame) -> PressureSeries:
    df = _normalize_columns(df.copy())
    if "time_hr" not in df.columns or "pressure_psi" not in df.columns:
        raise ValueError("DataFrame needs time_hr and pressure_psi.")
    df = df.dropna(subset=["time_hr", "pressure_psi"]).sort_values("time_hr")
    rate = df["rate_bpd"].to_numpy(dtype=float) if "rate_bpd" in df.columns else None
    return PressureSeries(
        time_hr=df["time_hr"].to_numpy(dtype=float),
        pressure_psi=df["pressure_psi"].to_numpy(dtype=float),
        rate_bpd=rate,
        source="dataframe",
    )


def detect_cycles(
    series: PressureSeries,
    rate_threshold_bpd: float = 10.0,
    min_shutin_hr: float = 0.15,
    min_points: int = 5,
) -> list[DSTCycle]:
    """
    Auto-detect flow and shut-in periods from rate history.
    If rate is missing, infer shut-in from near-zero rate proxy via pressure slope breaks.
    """
    t = series.time_hr
    n = len(t)
    if n < min_points:
        return []

    if series.rate_bpd is not None:
        rate = np.nan_to_num(series.rate_bpd, nan=0.0)
    else:
        # Proxy: low |dP/dt| after flow-like segment — mark as shut-in candidate
        dp = np.gradient(series.pressure_psi, t)
        rate = np.where(np.abs(dp) < np.nanpercentile(np.abs(dp), 35), 0.0, 100.0)

    is_flow = rate > rate_threshold_bpd
    cycles: list[DSTCycle] = []
    cycle_id = 0
    i = 0
    while i < n:
        target = is_flow[i]
        j = i
        while j < n and is_flow[j] == target:
            j += 1
        duration = t[j - 1] - t[i]
        kind = "flow" if target else "shut-in"
        if kind == "shut-in" and duration < min_shutin_hr:
            i = j
            continue
        seg_rate = rate[i:j]
        cycles.append(
            DSTCycle(
                cycle_id=cycle_id,
                kind=kind,
                start_idx=i,
                end_idx=j - 1,
                start_hr=float(t[i]),
                end_hr=float(t[j - 1]),
                duration_hr=float(duration),
                avg_rate_bpd=float(np.mean(seg_rate)) if len(seg_rate) else 0.0,
                q_ref_bpd=float(np.mean(seg_rate[seg_rate > rate_threshold_bpd])) if np.any(seg_rate > rate_threshold_bpd) else float(series.properties.q),
            )
        )
        cycle_id += 1
        i = j

    series.cycles = cycles
    return cycles


def split_buildups(series: PressureSeries) -> list[PressureSeries]:
    """Return one PressureSeries per shut-in buildup for per-cycle analysis."""
    if not series.cycles:
        detect_cycles(series)
    buildups: list[PressureSeries] = []
    for cycle in series.cycles:
        if cycle.kind != "shut-in":
            continue
        sl = slice(cycle.start_idx, cycle.end_idx + 1)
        buildups.append(
            PressureSeries(
                time_hr=series.time_hr[sl] - series.time_hr[cycle.start_idx],
                pressure_psi=series.pressure_psi[sl].copy(),
                rate_bpd=np.zeros(cycle.end_idx - cycle.start_idx + 1),
                source=f"{series.source} buildup #{cycle.cycle_id}",
                properties=series.properties,
                origin_time_hr=float(series.time_hr[cycle.start_idx]),
            )
        )
    return buildups


def attach_properties(series: PressureSeries, props: ReservoirProperties) -> PressureSeries:
    series.properties = props
    return series
