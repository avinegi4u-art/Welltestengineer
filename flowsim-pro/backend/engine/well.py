"""
Well and tubing pressure traverse model.

Integrates hydrostatic and friction pressure gradients along measured depth
using Beggs-Brill (default) or simplified drift-flux correlation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from engine.beggs_brill import segment_gradients as bb_segment_gradients
from engine.fluid import FluidModel, FluidProperties
from engine.heat_transfer import HeatTransferConfig, outlet_temperature


@dataclass
class TubingSegment:
    md_top_ft: float
    md_bottom_ft: float
    tvd_top_ft: float
    tvd_bottom_ft: float
    inner_diameter_in: float
    roughness_ft: float = 0.00015
    inclination_deg: float = 90.0


@dataclass
class WellGeometry:
    segments: list[TubingSegment] = field(default_factory=list)
    packer_depth_ft: float = 8000.0
    perforation_depth_ft: float = 8500.0
    choke_size_64_in: float = 32.0
    wellhead_pressure_psi: float = 500.0
    bottomhole_pressure_psi: float | None = None
    liquid_rate_stb_d: float = 2000.0


@dataclass
class ProfilePoint:
    md_ft: float
    tvd_ft: float
    pressure_psi: float
    temperature_f: float
    holdup: float
    dpdz_psi_ft: float
    segment_type: str


class WellModel:
    """Calculate pressure/temperature profiles along wellbore."""

    GRAVITY_FT_S2 = 32.174

    def __init__(
        self,
        fluid: FluidModel,
        geometry: WellGeometry,
        heat_config: HeatTransferConfig | None = None,
        flow_correlation: str = "beggs_brill",
    ) -> None:
        self.fluid = fluid
        self.geometry = geometry
        self.flow_correlation = flow_correlation
        self.heat_config = heat_config or HeatTransferConfig(
            ambient_temp_f=fluid.props.reservoir_temp_f - 30.0
        )

    def friction_factor(self, reynolds: float, roughness_ft: float, diameter_ft: float) -> float:
        """Colebrook-White friction factor (explicit approximation)."""
        if reynolds < 2100:
            return 64.0 / max(reynolds, 1.0)
        rel_rough = roughness_ft / max(diameter_ft, 1e-6)
        f = 0.02
        for _ in range(10):
            f = (-2.0 * math.log10(rel_rough / 3.7 + 2.51 / (reynolds * math.sqrt(f)))) ** -2
        return f

    def segment_pressure_drop(
        self,
        seg: TubingSegment,
        pressure_psi: float,
        temperature_f: float,
        liquid_rate_stb_d: float,
        direction: str = "upward",
    ) -> tuple[float, float, float]:
        """
        Calculate pressure change over segment (psi).
        Returns (delta_p, holdup, dpdz).
        """
        length_ft = abs(seg.md_bottom_ft - seg.md_top_ft)
        length_ft = max(length_ft, 1.0)
        diameter_ft = seg.inner_diameter_in / 12.0
        area_ft2 = math.pi * (diameter_ft / 2.0) ** 2

        state = self.fluid.mixture_properties(
            pressure_psi, temperature_f, liquid_rate_stb_d, seg.inclination_deg
        )

        if self.flow_correlation == "beggs_brill":
            bo = state.oil_fvf
            bw = state.water_fvf
            ql = liquid_rate_stb_d * (bo * (1 - state.water_cut) + bw * state.water_cut) / 86400.0
            qg = state.gas_rate_mscf_d * 1000.0 * state.gas_fvf / 86400.0
            rho_l = (
                state.oil_density_lb_ft3 * (1 - state.water_cut)
                + state.water_density_lb_ft3 * state.water_cut
            )
            mu_l = (
                state.oil_viscosity_cp * (1 - state.water_cut)
                + state.water_viscosity_cp * state.water_cut
            ) * 0.000672

            bb = bb_segment_gradients(
                diameter_ft=diameter_ft,
                roughness_ft=seg.roughness_ft,
                length_ft=length_ft,
                inclination_deg=seg.inclination_deg,
                superficial_liquid_ft_s=ql / area_ft2,
                superficial_gas_ft_s=qg / area_ft2,
                liquid_density_lb_ft3=rho_l,
                gas_density_lb_ft3=state.gas_density_lb_ft3,
                liquid_viscosity_lb_ft_s=mu_l,
                marching_downward=(direction == "downward"),
            )
            delta_p = bb.dpdz_total_psi_ft * length_ft
            return delta_p, bb.liquid_holdup, bb.dpdz_total_psi_ft

        rho = state.mixture_density_lb_ft3
        # Minimum density for gravity gradient in tubing (avoids gas-dominated instability)
        rho_grav = max(rho, 32.0 + 20.0 * state.liquid_holdup)
        mu = state.mixture_viscosity_cp * 0.000672  # cp to lb/(ft·s)

        # Superficial velocity ft/s
        bo = state.oil_fvf
        bw = state.water_fvf
        ql = liquid_rate_stb_d * (bo * (1 - state.water_cut) + bw * state.water_cut) / 86400.0
        qg = state.gas_rate_mscf_d * 1000.0 * state.gas_fvf / 86400.0
        vsl = ql / area_ft2
        vsg = qg / area_ft2
        vm = vsl + vsg

        re = max(rho * vm * diameter_ft / max(mu, 1e-8), 100.0)
        f = min(self.friction_factor(re, seg.roughness_ft, diameter_ft), 0.08)

        length_ft = max(length_ft, 1.0)
        # Friction gradient (psi/ft), capped for simplified correlation stability
        dpdz_friction = min(f * rho * vm**2 / (2.0 * diameter_ft * 144.0), 0.08)

        # Hydrostatic gradient along pipe axis (psi/ft)
        incl_rad = math.radians(seg.inclination_deg)
        dpdz_gravity = rho_grav * math.sin(incl_rad) / 144.0

        if direction == "downward":
            # Top-down march: pressure increases with depth minus friction
            dpdz_total = dpdz_gravity - dpdz_friction
            delta_p = dpdz_total * length_ft
        else:
            # Bottom-up march: pressure decreases toward surface
            dpdz_total = -(dpdz_gravity + dpdz_friction)
            delta_p = dpdz_total * length_ft

        return delta_p, state.liquid_holdup, dpdz_total

    def choke_pressure_drop(
        self,
        liquid_rate_stb_d: float,
        downstream_psi: float,
        temperature_f: float | None = None,
    ) -> float:
        """
        Multiphase choke ΔP (orifice form).

        Treats ``downstream_psi`` as pressure after the choke (line/separator side).
        Returns upstream−downstream drop so tubing WHP = downstream + ΔP.
        """
        bean_64 = self.geometry.choke_size_64_in
        if bean_64 <= 0:
            return 0.0
        choke_in = bean_64 / 64.0
        if choke_in <= 0:
            return 0.0

        t = temperature_f if temperature_f is not None else (self.heat_config.ambient_temp_f + 20.0)
        p_eval = max(downstream_psi, 14.7)
        state = self.fluid.mixture_properties(p_eval, t, liquid_rate_stb_d, 0.0)
        bo = state.oil_fvf
        bw = state.water_fvf
        ql = liquid_rate_stb_d * (bo * (1 - state.water_cut) + bw * state.water_cut) / 86400.0
        qg = state.gas_rate_mscf_d * 1000.0 * state.gas_fvf / 86400.0
        q_mix = ql + qg

        area_ft2 = math.pi * ((choke_in / 12.0) / 2.0) ** 2
        if area_ft2 <= 0:
            return 0.0

        cd = 0.85
        rho = max(state.mixture_density_lb_ft3, 1.0)
        velocity = q_mix / area_ft2
        # Bernoulli orifice: ΔP = ρ v² / (2 g_c Cd²) converted to psi
        dp_psi = rho * velocity**2 / (2.0 * self.GRAVITY_FT_S2 * cd**2) / 144.0
        # Cap extreme values for tiny beans / high rates
        return min(max(dp_psi, 0.0), max(downstream_psi * 3.0, 500.0))

    def effective_tubing_whp(
        self,
        downstream_whp_psi: float,
        liquid_rate_stb_d: float,
        temperature_f: float | None = None,
    ) -> tuple[float, float]:
        """Return (tubing-side WHP, choke ΔP) for VLP marches."""
        dp = self.choke_pressure_drop(liquid_rate_stb_d, downstream_whp_psi, temperature_f)
        return downstream_whp_psi + dp, dp

    def traverse_bottom_up(
        self,
        bhp_psi: float | None = None,
        liquid_rate: float | None = None,
    ) -> list[ProfilePoint]:
        """March from perforations to wellhead."""
        rate = liquid_rate or self.geometry.liquid_rate_stb_d
        p = bhp_psi or self.geometry.bottomhole_pressure_psi or 3000.0
        t = self.fluid.props.reservoir_temp_f
        profile: list[ProfilePoint] = []

        sorted_segs = sorted(self.geometry.segments, key=lambda s: s.md_top_ft, reverse=True)
        for seg in sorted_segs:
            md_points = np.linspace(seg.md_bottom_ft, seg.md_top_ft, max(2, int(abs(seg.md_bottom_ft - seg.md_top_ft) / 500)))
            for i, md in enumerate(md_points):
                if i == 0:
                    profile.append(
                        ProfilePoint(
                            md_ft=float(md),
                            tvd_ft=float(np.interp(md, [seg.md_top_ft, seg.md_bottom_ft], [seg.tvd_top_ft, seg.tvd_bottom_ft])),
                            pressure_psi=p,
                            temperature_f=t,
                            holdup=0.5,
                            dpdz_psi_ft=0.0,
                            segment_type="tubing",
                        )
                    )
                    continue
                sub_len = abs(md - md_points[i - 1])
                sub_seg = TubingSegment(
                    md_top_ft=float(md_points[i - 1]),
                    md_bottom_ft=float(md),
                    tvd_top_ft=float(np.interp(md_points[i - 1], [seg.md_top_ft, seg.md_bottom_ft], [seg.tvd_top_ft, seg.tvd_bottom_ft])),
                    tvd_bottom_ft=float(np.interp(md, [seg.md_top_ft, seg.md_bottom_ft], [seg.tvd_top_ft, seg.tvd_bottom_ft])),
                    inner_diameter_in=seg.inner_diameter_in,
                    roughness_ft=seg.roughness_ft,
                    inclination_deg=seg.inclination_deg,
                )
                dp, hl, dpdz = self.segment_pressure_drop(sub_seg, p, t, rate, "upward")
                p += dp
                mass_flow = rate * 50.0  # approximate lb/hr
                t = outlet_temperature(t, self.heat_config.ambient_temp_f, sub_len, mass_flow, 0.5,
                                       self.heat_config.overall_u_btu_hr_ft2_f, seg.inner_diameter_in)
                profile.append(
                    ProfilePoint(
                        md_ft=float(md),
                        tvd_ft=sub_seg.tvd_top_ft,
                        pressure_psi=p,
                        temperature_f=t,
                        holdup=hl,
                        dpdz_psi_ft=dpdz,
                        segment_type="tubing",
                    )
                )
        return profile

    def traverse_top_down(
        self,
        whp_psi: float | None = None,
        liquid_rate: float | None = None,
        apply_choke: bool = True,
    ) -> list[ProfilePoint]:
        """
        March from wellhead to bottomhole (VLP).

        ``whp_psi`` is the pressure downstream of the surface choke (line/separator).
        When ``apply_choke`` is True, tubing-side starting pressure includes choke ΔP.
        """
        rate = liquid_rate or self.geometry.liquid_rate_stb_d
        downstream = whp_psi if whp_psi is not None else self.geometry.wellhead_pressure_psi
        t = self.heat_config.ambient_temp_f + 20.0
        if apply_choke:
            p, _choke_dp = self.effective_tubing_whp(downstream, rate, t)
        else:
            p = downstream
        p = max(p, 14.7)
        profile: list[ProfilePoint] = []

        sorted_segs = sorted(self.geometry.segments, key=lambda s: s.md_top_ft)
        for seg in sorted_segs:
            md_points = np.linspace(seg.md_top_ft, seg.md_bottom_ft, max(2, int(abs(seg.md_bottom_ft - seg.md_top_ft) / 500)))
            for i, md in enumerate(md_points):
                if i == 0:
                    profile.append(
                        ProfilePoint(
                            md_ft=float(md),
                            tvd_ft=seg.tvd_top_ft,
                            pressure_psi=p,
                            temperature_f=t,
                            holdup=0.5,
                            dpdz_psi_ft=0.0,
                            segment_type="tubing",
                        )
                    )
                    continue
                sub_len = abs(md - md_points[i - 1])
                sub_seg = TubingSegment(
                    md_top_ft=float(md_points[i - 1]),
                    md_bottom_ft=float(md),
                    tvd_top_ft=float(np.interp(md_points[i - 1], [seg.md_top_ft, seg.md_bottom_ft], [seg.tvd_top_ft, seg.tvd_bottom_ft])),
                    tvd_bottom_ft=float(np.interp(md, [seg.md_top_ft, seg.md_bottom_ft], [seg.tvd_top_ft, seg.tvd_bottom_ft])),
                    inner_diameter_in=seg.inner_diameter_in,
                    roughness_ft=seg.roughness_ft,
                    inclination_deg=seg.inclination_deg,
                )
                dp, hl, dpdz = self.segment_pressure_drop(sub_seg, p, t, rate, "downward")
                p = max(p + dp, 14.7)
                mass_flow = rate * 50.0
                t = outlet_temperature(t, self.fluid.props.reservoir_temp_f, sub_len, mass_flow, 0.5,
                                       self.heat_config.overall_u_btu_hr_ft2_f * 0.3, seg.inner_diameter_in)
                profile.append(
                    ProfilePoint(
                        md_ft=float(md),
                        tvd_ft=sub_seg.tvd_bottom_ft,
                        pressure_psi=p,
                        temperature_f=t,
                        holdup=hl,
                        dpdz_psi_ft=dpdz,
                        segment_type="tubing",
                    )
                )
        return profile

    def to_dict(self) -> dict[str, Any]:
        return {
            "packer_depth_ft": self.geometry.packer_depth_ft,
            "perforation_depth_ft": self.geometry.perforation_depth_ft,
            "choke_size_64_in": self.geometry.choke_size_64_in,
            "segment_count": len(self.geometry.segments),
        }
