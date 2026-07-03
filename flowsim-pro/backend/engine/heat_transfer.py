"""Basic heat transfer model for wellbore and pipeline segments."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class HeatTransferConfig:
    ambient_temp_f: float = 70.0
    overall_u_btu_hr_ft2_f: float = 3.0
    burial_depth_ft: float = 0.0
    insulation_thickness_in: float = 0.0
    insulation_k_btu_hr_ft_f: float = 0.04


def segment_surface_area_ft2(diameter_in: float, length_ft: float) -> float:
    """External surface area of a cylindrical segment."""
    radius_ft = diameter_in / 24.0
    return 2.0 * math.pi * radius_ft * length_ft


def outlet_temperature(
    inlet_temp_f: float,
    ambient_temp_f: float,
    length_ft: float,
    mass_flow_lb_hr: float,
    cp_btu_lb_f: float,
    u_btu_hr_ft2_f: float,
    diameter_in: float,
) -> float:
    """
    Steady-state lumped heat balance: exponential approach to ambient.

    T_out = T_amb + (T_in - T_amb) * exp(-UA / (m_dot * Cp))
    """
    if mass_flow_lb_hr <= 0 or length_ft <= 0:
        return inlet_temp_f
    area = segment_surface_area_ft2(diameter_in, length_ft)
    ua = u_btu_hr_ft2_f * area
    exponent = -ua / (mass_flow_lb_hr * max(cp_btu_lb_f, 0.1))
    return ambient_temp_f + (inlet_temp_f - ambient_temp_f) * math.exp(exponent)


def temperature_profile(
    inlet_temp_f: float,
    config: HeatTransferConfig,
    segments: list[dict],
    mass_flow_lb_hr: float,
    cp_btu_lb_f: float = 0.5,
) -> list[float]:
    """Compute temperature at end of each segment."""
    temps: list[float] = [inlet_temp_f]
    current = inlet_temp_f
    u = config.overall_u_btu_hr_ft2_f
    if config.insulation_thickness_in > 0:
        # Simplified insulation resistance reduction
        u = max(0.5, u * 0.5)
    for seg in segments:
        current = outlet_temperature(
            current,
            config.ambient_temp_f,
            seg["length_ft"],
            mass_flow_lb_hr,
            cp_btu_lb_f,
            u,
            seg.get("diameter_in", 4.0),
        )
        temps.append(current)
    return temps
