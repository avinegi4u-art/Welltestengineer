"""
Flowline and pipeline pressure/temperature traverse model.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from engine.fluid import FluidModel
from engine.heat_transfer import HeatTransferConfig, outlet_temperature


@dataclass
class PipelineSegment:
    length_ft: float
    inner_diameter_in: float
    roughness_ft: float = 0.00015
    inclination_deg: float = 0.0
    elevation_change_ft: float = 0.0
    ambient_temp_f: float = 70.0
    u_btu_hr_ft2_f: float = 2.0


@dataclass
class PipelineGeometry:
    segments: list[PipelineSegment] = field(default_factory=list)
    inlet_pressure_psi: float = 400.0
    inlet_temperature_f: float = 120.0
    outlet_pressure_psi: float | None = None
    liquid_rate_stb_d: float = 2000.0


@dataclass
class PipelineProfilePoint:
    distance_ft: float
    pressure_psi: float
    temperature_f: float
    holdup: float
    velocity_ft_s: float


class PipelineModel:
    """Multiphase pipeline pressure and temperature profile."""

    def __init__(
        self,
        fluid: FluidModel,
        geometry: PipelineGeometry,
        heat_config: HeatTransferConfig | None = None,
    ) -> None:
        self.fluid = fluid
        self.geometry = geometry
        self.heat_config = heat_config or HeatTransferConfig()

    def friction_factor(self, reynolds: float, roughness_ft: float, diameter_ft: float) -> float:
        if reynolds < 2100:
            return 64.0 / max(reynolds, 1.0)
        rel_rough = roughness_ft / max(diameter_ft, 1e-6)
        return float(0.25 / (math.log10(rel_rough / 3.7 + 5.74 / reynolds**0.9) ** 2))

    def segment_dp(
        self,
        seg: PipelineSegment,
        pressure_psi: float,
        temperature_f: float,
        liquid_rate_stb_d: float,
    ) -> tuple[float, float, float]:
        length_ft = seg.length_ft
        diameter_ft = seg.inner_diameter_in / 12.0
        area_ft2 = math.pi * (diameter_ft / 2.0) ** 2

        state = self.fluid.mixture_properties(
            pressure_psi, temperature_f, liquid_rate_stb_d, seg.inclination_deg
        )
        rho = state.mixture_density_lb_ft3
        mu = state.mixture_viscosity_cp * 0.000672

        ql = liquid_rate_stb_d * 5.615 / 86400.0
        vm = ql / area_ft2
        re = max(rho * vm * diameter_ft / max(mu, 1e-8), 1.0)
        f = self.friction_factor(re, seg.roughness_ft, diameter_ft)

        re = max(rho * vm * diameter_ft / max(mu, 1e-8), 100.0)
        f = min(self.friction_factor(re, seg.roughness_ft, diameter_ft), 0.08)

        length_ft = max(length_ft, 1.0)
        dpdz_fric = min(f * rho * vm**2 / (2.0 * diameter_ft * 144.0), 0.05)
        incl_rad = math.radians(seg.inclination_deg)
        dpdz_grav = rho * math.sin(incl_rad) / 144.0
        dpdz_elev = rho * seg.elevation_change_ft / (length_ft * 144.0)
        dp = (dpdz_fric + abs(dpdz_elev)) * length_ft
        dpdz = dp / length_ft
        return dp, state.liquid_holdup, vm

    def traverse(
        self,
        inlet_pressure: float | None = None,
        liquid_rate: float | None = None,
    ) -> list[PipelineProfilePoint]:
        rate = liquid_rate or self.geometry.liquid_rate_stb_d
        p = inlet_pressure or self.geometry.inlet_pressure_psi
        t = self.geometry.inlet_temperature_f
        profile: list[PipelineProfilePoint] = []
        distance = 0.0

        for seg in self.geometry.segments:
            n_pts = max(2, int(seg.length_ft / 1000) + 1)
            dists = np.linspace(0, seg.length_ft, n_pts)
            for i, d in enumerate(dists):
                if i == 0 and not profile:
                    profile.append(
                        PipelineProfilePoint(
                            distance_ft=distance,
                            pressure_psi=p,
                            temperature_f=t,
                            holdup=0.5,
                            velocity_ft_s=0.0,
                        )
                    )
                    continue
                sub_len = abs(d - dists[i - 1]) if i > 0 else 0
                if sub_len > 0:
                    sub = PipelineSegment(
                        length_ft=sub_len,
                        inner_diameter_in=seg.inner_diameter_in,
                        roughness_ft=seg.roughness_ft,
                        inclination_deg=seg.inclination_deg,
                        elevation_change_ft=seg.elevation_change_ft * sub_len / seg.length_ft,
                        ambient_temp_f=seg.ambient_temp_f,
                        u_btu_hr_ft2_f=seg.u_btu_hr_ft2_f,
                    )
                    dp, hl, vm = self.segment_dp(sub, p, t, rate)
                    p = max(p - dp, 14.7)
                    mass_flow = rate * 50.0
                    t = outlet_temperature(
                        t, seg.ambient_temp_f, sub_len, mass_flow, 0.5, seg.u_btu_hr_ft2_f, seg.inner_diameter_in
                    )
                    distance += sub_len
                    profile.append(
                        PipelineProfilePoint(
                            distance_ft=distance,
                            pressure_psi=p,
                            temperature_f=t,
                            holdup=hl,
                            velocity_ft_s=vm,
                        )
                    )
        return profile

    def total_pressure_drop(self, liquid_rate: float | None = None) -> float:
        profile = self.traverse(liquid_rate=liquid_rate)
        if len(profile) < 2:
            return 0.0
        return profile[0].pressure_psi - profile[-1].pressure_psi

    def to_dict(self) -> dict[str, Any]:
        total_length = sum(s.length_ft for s in self.geometry.segments)
        return {"total_length_ft": total_length, "segment_count": len(self.geometry.segments)}
