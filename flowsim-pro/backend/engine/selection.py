"""
Phase B/C selection studies: tubing auto-sizing and flowline diameter sweep.

Tubing selector ranks catalog IDs by nodal operating rate, BHP, mixture
velocity, and API RP 14E erosional velocity screening.
Flowline selector sweeps pipe IDs for ΔP / velocity and recommends a
minimum diameter that meets a target pressure-drop constraint.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from engine.catalog import FLOWLINE_CATALOG, TUBING_CATALOG, PipeSize, TubingSize
from engine.fluid import FluidModel
from engine.nodal import NodalAnalyzer
from engine.pipeline import PipelineGeometry, PipelineModel, PipelineSegment
from engine.well import TubingSegment, WellGeometry, WellModel


def erosional_velocity_ft_s(mixture_density_lb_ft3: float, c_factor: float = 100.0) -> float:
    """API RP 14E erosional velocity Ve = C / sqrt(rho_mix) [ft/s]."""
    rho = max(mixture_density_lb_ft3, 1.0)
    return c_factor / math.sqrt(rho)


def mixture_velocity_at_wh(
    fluid: FluidModel,
    liquid_rate_stb_d: float,
    pressure_psi: float,
    temperature_f: float,
    inner_diameter_in: float,
) -> tuple[float, float]:
    """Return (mixture velocity ft/s, mixture density lb/ft3) at wellhead-like conditions."""
    diameter_ft = inner_diameter_in / 12.0
    area_ft2 = math.pi * (diameter_ft / 2.0) ** 2
    state = fluid.mixture_properties(pressure_psi, temperature_f, liquid_rate_stb_d, 90.0)
    bo = state.oil_fvf
    bw = state.water_fvf
    ql = liquid_rate_stb_d * (bo * (1 - state.water_cut) + bw * state.water_cut) / 86400.0
    qg = state.gas_rate_mscf_d * 1000.0 * state.gas_fvf / 86400.0
    vm = (ql + qg) / max(area_ft2, 1e-12)
    return vm, state.mixture_density_lb_ft3


@dataclass
class TubingCandidateResult:
    label: str
    od_in: float
    weight_lb_ft: float
    inner_diameter_in: float
    operating_rate_stb_d: float
    operating_bhp_psi: float
    status: str
    message: str
    max_mixture_velocity_ft_s: float
    erosional_velocity_ft_s: float
    erosion_ratio: float
    erosion_ok: bool
    choke_dp_psi: float
    rank_score: float
    recommended: bool = False


@dataclass
class TubingSelectionResult:
    candidates: list[TubingCandidateResult] = field(default_factory=list)
    recommended_label: str | None = None
    recommended_id_in: float | None = None
    diagnostics: list[str] = field(default_factory=list)
    c_factor: float = 100.0


@dataclass
class FlowlineCandidateResult:
    label: str
    nominal_in: float
    schedule: str
    inner_diameter_in: float
    pressure_drop_psi: float
    outlet_pressure_psi: float
    max_velocity_ft_s: float
    erosional_velocity_ft_s: float
    erosion_ratio: float
    erosion_ok: bool
    meets_dp_target: bool
    recommended: bool = False


@dataclass
class FlowlineSelectionResult:
    candidates: list[FlowlineCandidateResult] = field(default_factory=list)
    recommended_label: str | None = None
    recommended_id_in: float | None = None
    target_dp_psi: float = 50.0
    diagnostics: list[str] = field(default_factory=list)
    c_factor: float = 100.0


class TubingSelector:
    """Phase B — sweep tubing catalog through nodal analysis and rank candidates."""

    def __init__(
        self,
        fluid: FluidModel,
        well_geometry: WellGeometry,
        reservoir_pressure_psi: float,
        productivity_index: float,
        ipr_model: str = "pi",
        whp_psi: float | None = None,
        c_factor: float = 100.0,
        catalog: list[TubingSize] | None = None,
    ) -> None:
        self.fluid = fluid
        self.well_geometry = well_geometry
        self.pr = reservoir_pressure_psi
        self.pi = productivity_index
        self.ipr_model = ipr_model
        self.whp = whp_psi if whp_psi is not None else well_geometry.wellhead_pressure_psi
        self.c_factor = c_factor
        self.catalog = catalog or list(TUBING_CATALOG)

    def _copy_geo_with_id(self, id_in: float, roughness_ft: float) -> WellGeometry:
        segs = [
            TubingSegment(
                md_top_ft=s.md_top_ft,
                md_bottom_ft=s.md_bottom_ft,
                tvd_top_ft=s.tvd_top_ft,
                tvd_bottom_ft=s.tvd_bottom_ft,
                inner_diameter_in=id_in,
                roughness_ft=roughness_ft,
                inclination_deg=s.inclination_deg,
            )
            for s in self.well_geometry.segments
        ]
        return WellGeometry(
            segments=segs,
            packer_depth_ft=self.well_geometry.packer_depth_ft,
            perforation_depth_ft=self.well_geometry.perforation_depth_ft,
            choke_size_64_in=self.well_geometry.choke_size_64_in,
            wellhead_pressure_psi=self.well_geometry.wellhead_pressure_psi,
            liquid_rate_stb_d=self.well_geometry.liquid_rate_stb_d,
        )

    def evaluate(self) -> TubingSelectionResult:
        if not self.well_geometry.segments:
            return TubingSelectionResult(
                diagnostics=["No tubing segments defined — cannot run tubing selection."]
            )

        candidates: list[TubingCandidateResult] = []
        diagnostics: list[str] = []

        for size in self.catalog:
            geo = self._copy_geo_with_id(size.inner_diameter_in, size.roughness_ft)
            analyzer = NodalAnalyzer(
                self.fluid,
                geo,
                reservoir_pressure_psi=self.pr,
                productivity_index_stb_d_psi=self.pi,
                ipr_model=self.ipr_model,
                flow_correlation="beggs_brill",
            )
            nodal = analyzer.solve_operating_point(whp_psi=self.whp, geometry=geo)
            rate = nodal.operating_rate_stb_d
            well = WellModel(self.fluid, geo, flow_correlation="beggs_brill")
            choke_dp = well.choke_pressure_drop(rate, self.whp)
            vm, rho = mixture_velocity_at_wh(
                self.fluid, rate, self.whp + choke_dp, self.fluid.props.reservoir_temp_f - 40.0, size.inner_diameter_in
            )
            ve = erosional_velocity_ft_s(rho, self.c_factor)
            ratio = vm / max(ve, 1e-6)
            erosion_ok = ratio <= 1.0

            # Prefer higher rate, then erosion-safe, then lower BHP drawdown proxy
            rank = rate
            if not erosion_ok:
                rank -= 5000.0
            if nodal.status != "operating_point_found":
                rank -= 2000.0

            candidates.append(
                TubingCandidateResult(
                    label=size.label,
                    od_in=size.od_in,
                    weight_lb_ft=size.weight_lb_ft,
                    inner_diameter_in=size.inner_diameter_in,
                    operating_rate_stb_d=round(rate, 1),
                    operating_bhp_psi=round(nodal.operating_bhp_psi, 1),
                    status=nodal.status,
                    message=nodal.message,
                    max_mixture_velocity_ft_s=round(vm, 3),
                    erosional_velocity_ft_s=round(ve, 3),
                    erosion_ratio=round(ratio, 3),
                    erosion_ok=erosion_ok,
                    choke_dp_psi=round(choke_dp, 1),
                    rank_score=rank,
                )
            )
            diagnostics.append(
                f"{size.label}: {rate:.0f} stb/d, BHP {nodal.operating_bhp_psi:.0f} psi, "
                f"v={vm:.1f} ft/s (Ve={ve:.1f}), {nodal.status}"
            )

        candidates.sort(key=lambda c: c.rank_score, reverse=True)
        recommended = next((c for c in candidates if c.erosion_ok and c.status == "operating_point_found"), None)
        if recommended is None and candidates:
            recommended = candidates[0]
        if recommended:
            recommended.recommended = True

        return TubingSelectionResult(
            candidates=candidates,
            recommended_label=recommended.label if recommended else None,
            recommended_id_in=recommended.inner_diameter_in if recommended else None,
            diagnostics=diagnostics,
            c_factor=self.c_factor,
        )

    @staticmethod
    def to_dict(result: TubingSelectionResult) -> dict[str, Any]:
        return {
            "recommended_label": result.recommended_label,
            "recommended_id_in": result.recommended_id_in,
            "c_factor": result.c_factor,
            "diagnostics": result.diagnostics,
            "candidates": [
                {
                    "label": c.label,
                    "od_in": c.od_in,
                    "weight_lb_ft": c.weight_lb_ft,
                    "inner_diameter_in": c.inner_diameter_in,
                    "operating_rate_stb_d": c.operating_rate_stb_d,
                    "operating_bhp_psi": c.operating_bhp_psi,
                    "status": c.status,
                    "message": c.message,
                    "max_mixture_velocity_ft_s": c.max_mixture_velocity_ft_s,
                    "erosional_velocity_ft_s": c.erosional_velocity_ft_s,
                    "erosion_ratio": c.erosion_ratio,
                    "erosion_ok": c.erosion_ok,
                    "choke_dp_psi": c.choke_dp_psi,
                    "rank_score": round(c.rank_score, 1),
                    "recommended": c.recommended,
                }
                for c in result.candidates
            ],
        }


class FlowlineSelector:
    """Phase C — sweep flowline diameters for ΔP / velocity and recommend min ID."""

    def __init__(
        self,
        fluid: FluidModel,
        base_segments: list[PipelineSegment],
        inlet_pressure_psi: float,
        inlet_temperature_f: float,
        liquid_rate_stb_d: float,
        target_dp_psi: float = 50.0,
        c_factor: float = 100.0,
        catalog: list[PipeSize] | None = None,
    ) -> None:
        self.fluid = fluid
        self.base_segments = base_segments
        self.inlet_p = inlet_pressure_psi
        self.inlet_t = inlet_temperature_f
        self.rate = liquid_rate_stb_d
        self.target_dp = target_dp_psi
        self.c_factor = c_factor
        self.catalog = catalog or list(FLOWLINE_CATALOG)

    def evaluate(self) -> FlowlineSelectionResult:
        if not self.base_segments:
            # Default single segment if none defined
            base = [
                PipelineSegment(
                    length_ft=5000.0,
                    inner_diameter_in=6.065,
                    roughness_ft=0.00015,
                    inclination_deg=0.0,
                    elevation_change_ft=0.0,
                    ambient_temp_f=70.0,
                    u_btu_hr_ft2_f=2.0,
                )
            ]
        else:
            base = self.base_segments

        candidates: list[FlowlineCandidateResult] = []
        diagnostics: list[str] = []

        for size in self.catalog:
            segs = [
                PipelineSegment(
                    length_ft=s.length_ft,
                    inner_diameter_in=size.inner_diameter_in,
                    roughness_ft=size.roughness_ft,
                    inclination_deg=s.inclination_deg,
                    elevation_change_ft=s.elevation_change_ft,
                    ambient_temp_f=s.ambient_temp_f,
                    u_btu_hr_ft2_f=s.u_btu_hr_ft2_f,
                )
                for s in base
            ]
            geo = PipelineGeometry(
                segments=segs,
                inlet_pressure_psi=self.inlet_p,
                inlet_temperature_f=self.inlet_t,
                liquid_rate_stb_d=self.rate,
            )
            model = PipelineModel(self.fluid, geo, flow_correlation="beggs_brill")
            profile = model.traverse()
            if len(profile) < 2:
                dp = 0.0
                outlet = self.inlet_p
                vmax = 0.0
                rho = 50.0
            else:
                dp = profile[0].pressure_psi - profile[-1].pressure_psi
                outlet = profile[-1].pressure_psi
                vmax = max(p.velocity_ft_s for p in profile)
                state = self.fluid.mixture_properties(self.inlet_p, self.inlet_t, self.rate, 0.0)
                rho = state.mixture_density_lb_ft3

            ve = erosional_velocity_ft_s(rho, self.c_factor)
            ratio = vmax / max(ve, 1e-6)
            erosion_ok = ratio <= 1.0
            meets = dp <= self.target_dp and erosion_ok

            candidates.append(
                FlowlineCandidateResult(
                    label=size.label,
                    nominal_in=size.nominal_in,
                    schedule=size.schedule,
                    inner_diameter_in=size.inner_diameter_in,
                    pressure_drop_psi=round(dp, 2),
                    outlet_pressure_psi=round(outlet, 2),
                    max_velocity_ft_s=round(vmax, 3),
                    erosional_velocity_ft_s=round(ve, 3),
                    erosion_ratio=round(ratio, 3),
                    erosion_ok=erosion_ok,
                    meets_dp_target=meets,
                )
            )
            diagnostics.append(
                f"{size.label}: ΔP={dp:.1f} psi, v={vmax:.1f} ft/s "
                f"(target ΔP≤{self.target_dp:.0f}, Ve={ve:.1f})"
            )

        # Recommend smallest ID that meets ΔP + erosion (min capital)
        meets_list = [c for c in candidates if c.meets_dp_target]
        if meets_list:
            recommended = min(meets_list, key=lambda c: c.inner_diameter_in)
        else:
            # Fall back to lowest ΔP among erosion-safe, else lowest ΔP overall
            safe = [c for c in candidates if c.erosion_ok]
            pool = safe or candidates
            recommended = min(pool, key=lambda c: c.pressure_drop_psi) if pool else None

        if recommended:
            recommended.recommended = True

        return FlowlineSelectionResult(
            candidates=candidates,
            recommended_label=recommended.label if recommended else None,
            recommended_id_in=recommended.inner_diameter_in if recommended else None,
            target_dp_psi=self.target_dp,
            diagnostics=diagnostics,
            c_factor=self.c_factor,
        )

    @staticmethod
    def to_dict(result: FlowlineSelectionResult) -> dict[str, Any]:
        return {
            "recommended_label": result.recommended_label,
            "recommended_id_in": result.recommended_id_in,
            "target_dp_psi": result.target_dp_psi,
            "c_factor": result.c_factor,
            "diagnostics": result.diagnostics,
            "candidates": [
                {
                    "label": c.label,
                    "nominal_in": c.nominal_in,
                    "schedule": c.schedule,
                    "inner_diameter_in": c.inner_diameter_in,
                    "pressure_drop_psi": c.pressure_drop_psi,
                    "outlet_pressure_psi": c.outlet_pressure_psi,
                    "max_velocity_ft_s": c.max_velocity_ft_s,
                    "erosional_velocity_ft_s": c.erosional_velocity_ft_s,
                    "erosion_ratio": c.erosion_ratio,
                    "erosion_ok": c.erosion_ok,
                    "meets_dp_target": c.meets_dp_target,
                    "recommended": c.recommended,
                }
                for c in result.candidates
            ],
        }
