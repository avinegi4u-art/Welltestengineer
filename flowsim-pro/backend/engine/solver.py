"""
Main simulation solver orchestrating all physics modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from engine.fluid import FluidModel, FluidProperties
from engine.heat_transfer import HeatTransferConfig
from engine.network import NetworkGeometry, NetworkNode, NetworkBranch, NetworkSolver
from engine.nodal import NodalAnalyzer
from engine.pipeline import PipelineGeometry, PipelineModel, PipelineSegment
from engine.well import TubingSegment, WellGeometry, WellModel


ASSUMPTIONS = {
    "fluid_model": "Black-oil with Standing Bo and Beggs-Robinson viscosity",
    "multiphase_flow": "Simplified drift-flux holdup with Darcy-Weisbach friction",
    "heat_transfer": "Steady-state lumped UA exponential approach to ambient",
    "ipr_models": ["Linear PI", "Vogel"],
    "network_solver": "Iterative pressure balance (Gauss-Seidel relaxation)",
    "units": "Field units (psi, ft, stb/d, °F)",
}


@dataclass
class SimulationInput:
    case_name: str = "Untitled Case"
    case_type: str = "well_tubing_flowline"  # well_tubing_flowline | nodal | network
    fluid: dict[str, Any] = field(default_factory=dict)
    well: dict[str, Any] = field(default_factory=dict)
    flowline: dict[str, Any] = field(default_factory=dict)
    nodal: dict[str, Any] = field(default_factory=dict)
    network: dict[str, Any] = field(default_factory=dict)
    heat_transfer: dict[str, Any] = field(default_factory=dict)
    boundary_conditions: dict[str, Any] = field(default_factory=dict)


@dataclass
class SimulationOutput:
    success: bool
    warnings: list[str]
    assumptions: dict[str, Any]
    fluid_summary: dict[str, Any]
    well_profile: list[dict[str, Any]]
    flowline_profile: list[dict[str, Any]]
    nodal_analysis: dict[str, Any] | None
    network_results: dict[str, Any] | None
    summary: dict[str, Any]
    diagnostics: list[str]


class SimulationSolver:
    """End-to-end steady-state multiphase flow solver."""

    def __init__(self, case_input: dict[str, Any] | SimulationInput) -> None:
        if isinstance(case_input, dict):
            self.input = SimulationInput(**{k: v for k, v in case_input.items() if k in SimulationInput.__dataclass_fields__})
        else:
            self.input = case_input
        self.warnings: list[str] = []
        self.diagnostics: list[str] = []

    def _build_fluid(self) -> FluidModel:
        props = FluidProperties(**{k: v for k, v in self.input.fluid.items() if hasattr(FluidProperties, k) or k in FluidProperties.__dataclass_fields__})
        self.warnings.extend(props.validate())
        return FluidModel(props)

    def _build_heat_config(self) -> HeatTransferConfig:
        ht = self.input.heat_transfer
        return HeatTransferConfig(
            ambient_temp_f=ht.get("ambient_temp_f", 70.0),
            overall_u_btu_hr_ft2_f=ht.get("overall_u_btu_hr_ft2_f", 3.0),
            burial_depth_ft=ht.get("burial_depth_ft", 0.0),
            insulation_thickness_in=ht.get("insulation_thickness_in", 0.0),
        )

    def _build_well_geometry(self, fluid: FluidModel) -> WellGeometry:
        w = self.input.well
        segments = [
            TubingSegment(
                md_top_ft=s["md_top_ft"],
                md_bottom_ft=s["md_bottom_ft"],
                tvd_top_ft=s.get("tvd_top_ft", s["md_top_ft"]),
                tvd_bottom_ft=s.get("tvd_bottom_ft", s["md_bottom_ft"]),
                inner_diameter_in=s.get("inner_diameter_in", 3.958),
                roughness_ft=s.get("roughness_ft", 0.00015),
                inclination_deg=s.get("inclination_deg", 90.0),
            )
            for s in w.get("segments", [])
        ]
        bc = self.input.boundary_conditions
        return WellGeometry(
            segments=segments,
            packer_depth_ft=w.get("packer_depth_ft", 8000),
            perforation_depth_ft=w.get("perforation_depth_ft", 8500),
            choke_size_64_in=w.get("choke_size_64_in", 32),
            wellhead_pressure_psi=bc.get("wellhead_pressure_psi", w.get("wellhead_pressure_psi", 500)),
            bottomhole_pressure_psi=bc.get("bottomhole_pressure_psi"),
            liquid_rate_stb_d=bc.get("liquid_rate_stb_d", 2000),
        )

    def _build_pipeline_geometry(self, inlet_p: float, inlet_t: float, rate: float) -> PipelineGeometry:
        f = self.input.flowline
        segments = [
            PipelineSegment(
                length_ft=s["length_ft"],
                inner_diameter_in=s.get("inner_diameter_in", 6.0),
                roughness_ft=s.get("roughness_ft", 0.00015),
                inclination_deg=s.get("inclination_deg", 0.0),
                elevation_change_ft=s.get("elevation_change_ft", 0.0),
                ambient_temp_f=s.get("ambient_temp_f", 70.0),
                u_btu_hr_ft2_f=s.get("u_btu_hr_ft2_f", 2.0),
            )
            for s in f.get("segments", [])
        ]
        return PipelineGeometry(
            segments=segments,
            inlet_pressure_psi=inlet_p,
            inlet_temperature_f=inlet_t,
            liquid_rate_stb_d=rate,
        )

    def solve(self) -> SimulationOutput:
        try:
            fluid = self._build_fluid()
            heat = self._build_heat_config()
            bc = self.input.boundary_conditions

            well_profile: list[dict] = []
            flowline_profile: list[dict] = []
            nodal_result = None
            network_result = None
            summary: dict[str, Any] = {}

            rate = bc.get("liquid_rate_stb_d", 2000)
            whp = bc.get("wellhead_pressure_psi", 500)
            bhp = bc.get("bottomhole_pressure_psi")

            # Well + tubing traverse
            well_geo = self._build_well_geometry(fluid)
            well_model = WellModel(fluid, well_geo, heat)

            if bhp:
                profile = well_model.traverse_bottom_up(bhp_psi=bhp, liquid_rate=rate)
                self.diagnostics.append(f"Bottom-up traverse from BHP={bhp:.0f} psi")
            else:
                profile = well_model.traverse_top_down(whp_psi=whp, liquid_rate=rate)
                bhp = profile[-1].pressure_psi if profile else whp
                self.diagnostics.append(f"Top-down VLP traverse from WHP={whp:.0f} psi")

            well_profile = [
                {
                    "md_ft": p.md_ft,
                    "tvd_ft": p.tvd_ft,
                    "pressure_psi": round(p.pressure_psi, 2),
                    "temperature_f": round(p.temperature_f, 2),
                    "holdup": round(p.holdup, 4),
                    "dpdz_psi_ft": round(p.dpdz_psi_ft, 6),
                }
                for p in profile
            ]

            whp_actual = profile[0].pressure_psi if profile else whp
            whp_temp = profile[0].temperature_f if profile else 120

            # Flowline traverse
            if self.input.flowline.get("segments"):
                pipe_geo = self._build_pipeline_geometry(whp_actual, whp_temp, rate)
                pipe_model = PipelineModel(fluid, pipe_geo, heat)
                fprofile = pipe_model.traverse()
                flowline_profile = [
                    {
                        "distance_ft": p.distance_ft,
                        "pressure_psi": round(p.pressure_psi, 2),
                        "temperature_f": round(p.temperature_f, 2),
                        "holdup": round(p.holdup, 4),
                        "velocity_ft_s": round(p.velocity_ft_s, 4),
                    }
                    for p in fprofile
                ]
                summary["flowline_outlet_pressure_psi"] = fprofile[-1].pressure_psi if fprofile else whp_actual
                summary["flowline_pressure_drop_psi"] = (
                    fprofile[0].pressure_psi - fprofile[-1].pressure_psi if fprofile else 0
                )

            summary.update(
                {
                    "liquid_rate_stb_d": rate,
                    "wellhead_pressure_psi": round(whp_actual, 2),
                    "bottomhole_pressure_psi": round(bhp or 0, 2),
                    "drawdown_psi": round((bhp or 0) - fluid.props.bubble_point_psi, 2),
                    "total_well_md_ft": max((p.md_ft for p in profile), default=0),
                }
            )

            # Nodal analysis
            if self.input.case_type in ("nodal", "well_tubing_flowline") or self.input.nodal:
                nodal_cfg = self.input.nodal
                analyzer = NodalAnalyzer(
                    fluid,
                    well_geo,
                    reservoir_pressure_psi=nodal_cfg.get("reservoir_pressure_psi", 3500),
                    productivity_index_stb_d_psi=nodal_cfg.get("productivity_index", 2.0),
                    ipr_model=nodal_cfg.get("ipr_model", "pi"),
                )
                nodal = analyzer.solve_operating_point(whp_psi=whp)
                nodal_result = {
                    "rates_stb_d": nodal.rates_stb_d,
                    "ipr_pressures_psi": [round(p, 2) for p in nodal.ipr_pressures_psi],
                    "vlp_pressures_psi": [round(p, 2) for p in nodal.vlp_pressures_psi],
                    "operating_rate_stb_d": round(nodal.operating_rate_stb_d, 2),
                    "operating_bhp_psi": round(nodal.operating_bhp_psi, 2),
                    "operating_whp_psi": round(nodal.operating_whp_psi, 2),
                    "convergence_error_psi": round(nodal.convergence_error, 4),
                }
                summary["nodal_operating_rate_stb_d"] = nodal.operating_rate_stb_d

            # Network solver
            if self.input.case_type == "network" and self.input.network:
                net_cfg = self.input.network
                nodes = [NetworkNode(**n) for n in net_cfg.get("nodes", [])]
                branches = [NetworkBranch(**b) for b in net_cfg.get("branches", [])]
                net_geo = NetworkGeometry(
                    nodes=nodes,
                    branches=branches,
                    separator_pressure_psi=net_cfg.get("separator_pressure_psi", 100),
                )
                solver = NetworkSolver(fluid, net_geo)
                result = solver.solve()
                network_result = {
                    "node_pressures": {k: round(v, 2) for k, v in result.node_pressures.items()},
                    "branch_rates": {k: round(v, 2) for k, v in result.branch_rates.items()},
                    "branch_pressure_drops": {k: round(v, 2) for k, v in result.branch_pressure_drops.items()},
                    "total_liquid_rate_stb_d": round(result.total_liquid_rate_stb_d, 2),
                    "converged": result.converged,
                    "iterations": result.iterations,
                }

            return SimulationOutput(
                success=True,
                warnings=self.warnings,
                assumptions=ASSUMPTIONS,
                fluid_summary=fluid.to_dict(),
                well_profile=well_profile,
                flowline_profile=flowline_profile,
                nodal_analysis=nodal_result,
                network_results=network_result,
                summary=summary,
                diagnostics=self.diagnostics,
            )
        except Exception as exc:
            return SimulationOutput(
                success=False,
                warnings=self.warnings + [str(exc)],
                assumptions=ASSUMPTIONS,
                fluid_summary={},
                well_profile=[],
                flowline_profile=[],
                nodal_analysis=None,
                network_results=None,
                summary={},
                diagnostics=self.diagnostics + [f"Solver error: {exc}"],
            )

    @staticmethod
    def compare_cases(outputs: list[dict[str, Any]]) -> dict[str, Any]:
        """Compare multiple case results side-by-side."""
        comparison = {
            "cases": [],
            "metrics": ["liquid_rate_stb_d", "wellhead_pressure_psi", "bottomhole_pressure_psi"],
        }
        for i, out in enumerate(outputs):
            summary = out.get("summary", {})
            comparison["cases"].append(
                {
                    "index": i,
                    "liquid_rate_stb_d": summary.get("liquid_rate_stb_d"),
                    "wellhead_pressure_psi": summary.get("wellhead_pressure_psi"),
                    "bottomhole_pressure_psi": summary.get("bottomhole_pressure_psi"),
                    "flowline_pressure_drop_psi": summary.get("flowline_pressure_drop_psi"),
                    "nodal_operating_rate_stb_d": summary.get("nodal_operating_rate_stb_d"),
                }
            )
        return comparison
