"""
Nodal analysis: IPR and VLP curves with operating point intersection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from engine.fluid import FluidModel
from engine.well import WellGeometry, WellModel


@dataclass
class NodalResult:
    rates_stb_d: list[float]
    ipr_pressures_psi: list[float]
    vlp_pressures_psi: list[float]
    operating_rate_stb_d: float
    operating_bhp_psi: float
    operating_whp_psi: float
    convergence_error: float


class NodalAnalyzer:
    """Generate IPR/VLP curves and find operating point."""

    def __init__(
        self,
        fluid: FluidModel,
        well_geometry: WellGeometry,
        reservoir_pressure_psi: float = 3500.0,
        productivity_index_stb_d_psi: float = 2.0,
        ipr_model: str = "pi",  # pi | vogel | fetkovich
    ) -> None:
        self.fluid = fluid
        self.well_geometry = well_geometry
        self.reservoir_pressure = reservoir_pressure_psi
        self.pi = productivity_index_stb_d_psi
        self.ipr_model = ipr_model

    def ipr_pressure(self, rate_stb_d: float) -> float:
        """Inflow performance: BHP vs rate."""
        if self.ipr_model == "vogel":
            q_max = self.pi * self.reservoir_pressure
            if q_max <= 0:
                return self.reservoir_pressure
            ratio = rate_stb_d / q_max
            if ratio >= 1.0:
                return 0.0
            return self.reservoir_pressure * (1.0 - 0.2 * ratio - 0.8 * ratio**2)
        # Linear PI model
        return max(0.0, self.reservoir_pressure - rate_stb_d / self.pi)

    def vlp_pressure(self, rate_stb_d: float, whp_psi: float | None = None) -> float:
        """Vertical lift performance: BHP required for given rate."""
        well = WellModel(self.fluid, self.well_geometry)
        whp = whp_psi or self.well_geometry.wellhead_pressure_psi
        profile = well.traverse_top_down(whp_psi=whp, liquid_rate=rate_stb_d)
        return profile[-1].pressure_psi if profile else whp

    def solve_operating_point(
        self,
        whp_psi: float | None = None,
        rate_guess: float = 1500.0,
    ) -> NodalResult:
        """Find rate where IPR and VLP intersect."""
        whp = whp_psi or self.well_geometry.wellhead_pressure_psi
        rates = np.linspace(100, 5000, 50)
        ipr_p = [self.ipr_pressure(r) for r in rates]
        vlp_p = [self.vlp_pressure(r, whp) for r in rates]

        diff = np.array(ipr_p) - np.array(vlp_p)
        sign_changes = np.where(np.diff(np.sign(diff)))[0]
        if len(sign_changes) > 0:
            idx = sign_changes[0]
            r1, r2 = rates[idx], rates[idx + 1]
            p1, p2 = diff[idx], diff[idx + 1]
            op_rate = r1 - p1 * (r2 - r1) / (p2 - p1)
            op_bhp = self.ipr_pressure(op_rate)
            error = abs(self.ipr_pressure(op_rate) - self.vlp_pressure(op_rate, whp))
        else:
            op_rate = float(rate_guess)
            op_bhp = self.ipr_pressure(op_rate)
            error = abs(self.ipr_pressure(op_rate) - self.vlp_pressure(op_rate, whp))

        return NodalResult(
            rates_stb_d=rates.tolist(),
            ipr_pressures_psi=ipr_p,
            vlp_pressures_psi=vlp_p,
            operating_rate_stb_d=float(op_rate),
            operating_bhp_psi=float(op_bhp),
            operating_whp_psi=whp,
            convergence_error=float(error),
        )

    def sensitivity(
        self,
        parameter: str,
        values: list[float],
        base_whp: float | None = None,
    ) -> list[dict[str, Any]]:
        """Run nodal analysis across parameter values."""
        results = []
        for val in values:
            geo = WellGeometry(
                segments=self.well_geometry.segments,
                packer_depth_ft=self.well_geometry.packer_depth_ft,
                perforation_depth_ft=self.well_geometry.perforation_depth_ft,
                choke_size_64_in=self.well_geometry.choke_size_64_in,
                wellhead_pressure_psi=self.well_geometry.wellhead_pressure_psi,
                liquid_rate_stb_d=self.well_geometry.liquid_rate_stb_d,
            )
            whp = base_whp or geo.wellhead_pressure_psi
            if parameter == "choke_size":
                geo.choke_size_64_in = val
            elif parameter == "whp":
                whp = val
            elif parameter == "tubing_id":
                for seg in geo.segments:
                    seg.inner_diameter_in = val
            elif parameter == "gor":
                self.fluid.props.gor_scf_stb = val
            elif parameter == "water_cut":
                self.fluid.props.water_cut = val

            analyzer = NodalAnalyzer(
                self.fluid, geo, self.reservoir_pressure, self.pi, self.ipr_model
            )
            nodal = analyzer.solve_operating_point(whp_psi=whp)
            results.append(
                {
                    "parameter": parameter,
                    "value": val,
                    "operating_rate_stb_d": nodal.operating_rate_stb_d,
                    "operating_bhp_psi": nodal.operating_bhp_psi,
                }
            )
        return results
