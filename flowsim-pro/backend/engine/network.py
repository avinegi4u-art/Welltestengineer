"""
Simple tree network solver for production gathering systems.

Iteratively balances branch flow rates and node pressures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy.optimize import root

from engine.fluid import FluidModel
from engine.pipeline import PipelineGeometry, PipelineModel, PipelineSegment
from engine.well import WellGeometry, WellModel


@dataclass
class NetworkNode:
    id: str
    node_type: str  # wellhead | junction | separator | export
    pressure_psi: float = 100.0
    is_fixed_pressure: bool = False


@dataclass
class NetworkBranch:
    id: str
    from_node: str
    to_node: str
    branch_type: str  # well | flowline | pipeline
    liquid_rate_stb_d: float = 1000.0
  # well or pipeline config stored as dict
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class NetworkGeometry:
    nodes: list[NetworkNode] = field(default_factory=list)
    branches: list[NetworkBranch] = field(default_factory=list)
    separator_pressure_psi: float = 100.0


@dataclass
class NetworkResult:
    node_pressures: dict[str, float]
    branch_rates: dict[str, float]
    branch_pressure_drops: dict[str, float]
    total_liquid_rate_stb_d: float
    converged: bool
    iterations: int


class NetworkSolver:
    """Solve pressure balance in tree production network."""

    def __init__(self, fluid: FluidModel, geometry: NetworkGeometry) -> None:
        self.fluid = fluid
        self.geometry = geometry

    def branch_outlet_pressure(
        self, branch: NetworkBranch, inlet_p: float, rate: float
    ) -> float:
        """Calculate outlet pressure for a branch given inlet P and rate."""
        if branch.branch_type == "well":
            geo = self._well_geometry_from_config(branch.config, rate)
            well = WellModel(self.fluid, geo)
            profile = well.traverse_bottom_up(
                bhp_psi=inlet_p, liquid_rate=rate
            )
            return profile[-1].pressure_psi if profile else inlet_p
        else:
            geo = self._pipeline_geometry_from_config(branch.config, inlet_p, rate)
            pipe = PipelineModel(self.fluid, geo)
            profile = pipe.traverse(inlet_pressure=inlet_p, liquid_rate=rate)
            return profile[-1].pressure_psi if profile else inlet_p

    def branch_inlet_pressure_for_outlet(
        self, branch: NetworkBranch, outlet_p: float, rate: float
    ) -> float:
        """Back-calculate inlet pressure needed for target outlet."""
        if branch.branch_type == "well":
            geo = self._well_geometry_from_config(branch.config, rate)
            geo.wellhead_pressure_psi = outlet_p
            well = WellModel(self.fluid, geo)
            profile = well.traverse_top_down(whp_psi=outlet_p, liquid_rate=rate)
            return profile[-1].pressure_psi if profile else outlet_p
        else:
            dp = PipelineModel(
                self.fluid,
                self._pipeline_geometry_from_config(branch.config, outlet_p + 50, rate),
            ).total_pressure_drop(rate)
            return outlet_p + dp

    def _well_geometry_from_config(self, config: dict, rate: float) -> WellGeometry:
        from engine.well import TubingSegment

        segments = [
            TubingSegment(**s) for s in config.get("segments", [])
        ]
        return WellGeometry(
            segments=segments,
            packer_depth_ft=config.get("packer_depth_ft", 8000),
            perforation_depth_ft=config.get("perforation_depth_ft", 8500),
            choke_size_64_in=config.get("choke_size_64_in", 32),
            wellhead_pressure_psi=config.get("wellhead_pressure_psi", 500),
            liquid_rate_stb_d=rate,
        )

    def _pipeline_geometry_from_config(
        self, config: dict, inlet_p: float, rate: float
    ) -> PipelineGeometry:
        segments = [PipelineSegment(**s) for s in config.get("segments", [])]
        return PipelineGeometry(
            segments=segments,
            inlet_pressure_psi=inlet_p,
            inlet_temperature_f=config.get("inlet_temperature_f", 120),
            liquid_rate_stb_d=rate,
        )

    def solve(self, max_iterations: int = 50, tolerance: float = 1.0) -> NetworkResult:
        """
        Iterative network solver for tree topology.
        Fixed separator pressure; solve well rates to match.
        """
        node_p: dict[str, float] = {n.id: n.pressure_psi for n in self.geometry.nodes}
        branch_rates: dict[str, float] = {
            b.id: b.liquid_rate_stb_d for b in self.geometry.branches
        }

        sep_node = next(
            (n for n in self.geometry.nodes if n.node_type == "separator"),
            self.geometry.nodes[-1] if self.geometry.nodes else None,
        )
        if sep_node:
            node_p[sep_node.id] = self.geometry.separator_pressure_psi

        converged = False
        for iteration in range(max_iterations):
            max_error = 0.0
            branch_dp: dict[str, float] = {}

            for branch in self.geometry.branches:
                if branch.branch_type == "well":
                    wh_node = branch.to_node
                    wh_p = node_p.get(wh_node, 500)
                    bhp = self.branch_inlet_pressure_for_outlet(branch, wh_p, branch_rates[branch.id])
                    branch_dp[branch.id] = bhp - wh_p
                else:
                    inlet_node = branch.from_node
                    outlet_node = branch.to_node
                    inlet_p = node_p.get(inlet_node, 500)
                    outlet_p = self.branch_outlet_pressure(branch, inlet_p, branch_rates[branch.id])
                    branch_dp[branch.id] = inlet_p - outlet_p
                    if not any(
                        n.id == outlet_node and n.is_fixed_pressure
                        for n in self.geometry.nodes
                    ):
                        old_p = node_p.get(outlet_node, outlet_p)
                        node_p[outlet_node] = 0.7 * old_p + 0.3 * outlet_p
                        max_error = max(max_error, abs(old_p - node_p[outlet_node]))

            if max_error < tolerance:
                converged = True
                break

        total_rate = sum(
            branch_rates[b.id]
            for b in self.geometry.branches
            if b.branch_type == "well"
        )

        return NetworkResult(
            node_pressures=node_p,
            branch_rates=branch_rates,
            branch_pressure_drops=branch_dp,
            total_liquid_rate_stb_d=total_rate,
            converged=converged,
            iterations=iteration + 1,
        )
