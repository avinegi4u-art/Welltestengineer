"""
Nodal analysis: IPR and VLP curves with operating point intersection.
Phase A: Beggs-Brill VLP, sensitivity sweeps, diagnostic status messages.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any

import numpy as np

from engine.fluid import FluidModel, FluidProperties
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
    status: str = "unknown"
    message: str = ""
    aof_stb_d: float = 0.0


@dataclass
class SensitivityCurve:
    parameter: str
    value: float
    label: str
    rates_stb_d: list[float]
    vlp_pressures_psi: list[float]
    operating_rate_stb_d: float
    operating_bhp_psi: float
    status: str
    message: str


@dataclass
class SensitivityResult:
    parameter: str
    ipr_rates_stb_d: list[float]
    ipr_pressures_psi: list[float]
    curves: list[SensitivityCurve] = field(default_factory=list)
    diagnostics: list[str] = field(default_factory=list)


class NodalAnalyzer:
    """Generate IPR/VLP curves and find operating point."""

    def __init__(
        self,
        fluid: FluidModel,
        well_geometry: WellGeometry,
        reservoir_pressure_psi: float = 3500.0,
        productivity_index_stb_d_psi: float = 2.0,
        ipr_model: str = "pi",
        flow_correlation: str = "beggs_brill",
    ) -> None:
        self.fluid = fluid
        self.well_geometry = well_geometry
        self.reservoir_pressure = reservoir_pressure_psi
        self.pi = productivity_index_stb_d_psi
        self.ipr_model = ipr_model
        self.flow_correlation = flow_correlation

    def aof_rate(self) -> float:
        """Absolute open flow (stb/d) for IPR curve endpoint."""
        if self.ipr_model == "vogel":
            return self.pi * self.reservoir_pressure
        return self.reservoir_pressure * self.pi

    def ipr_pressure(self, rate_stb_d: float) -> float:
        """Inflow performance: BHP vs rate."""
        if self.ipr_model == "vogel":
            q_max = self.aof_rate()
            if q_max <= 0:
                return self.reservoir_pressure
            ratio = rate_stb_d / q_max
            if ratio >= 1.0:
                return 0.0
            return self.reservoir_pressure * (1.0 - 0.2 * ratio - 0.8 * ratio ** 2)
        return max(0.0, self.reservoir_pressure - rate_stb_d / self.pi)

    def _well_model(self, geometry: WellGeometry | None = None) -> WellModel:
        geo = geometry or self.well_geometry
        return WellModel(self.fluid, geo, flow_correlation=self.flow_correlation)

    def vlp_pressure(self, rate_stb_d: float, whp_psi: float | None = None, geometry: WellGeometry | None = None) -> float:
        """Vertical lift performance: BHP required for given rate (Beggs-Brill VLP)."""
        well = self._well_model(geometry)
        whp = whp_psi if whp_psi is not None else (geometry or self.well_geometry).wellhead_pressure_psi
        profile = well.traverse_top_down(whp_psi=whp, liquid_rate=rate_stb_d)
        return profile[-1].pressure_psi if profile else whp

    def generate_vlp_curve(
        self,
        whp_psi: float | None = None,
        geometry: WellGeometry | None = None,
        rate_min: float = 100.0,
        rate_max: float | None = None,
        n_points: int = 50,
    ) -> tuple[list[float], list[float]]:
        """Generate VLP pressures over a rate range."""
        whp = whp_psi if whp_psi is not None else self.well_geometry.wellhead_pressure_psi
        q_max = rate_max or max(self.aof_rate() * 1.2, 3000.0)
        rates = np.linspace(rate_min, q_max, n_points)
        vlp = [self.vlp_pressure(float(r), whp, geometry) for r in rates]
        return rates.tolist(), vlp

    def _classify_intersection(
        self,
        rates: np.ndarray,
        ipr_p: list[float],
        vlp_p: list[float],
        whp: float,
    ) -> tuple[float, float, float, str, str]:
        """Find operating point and return rate, bhp, error, status, message."""
        diff = np.array(ipr_p) - np.array(vlp_p)
        sign_changes = np.where(np.diff(np.sign(diff)))[0]

        if len(sign_changes) > 0:
            idx = int(sign_changes[0])
            r1, r2 = rates[idx], rates[idx + 1]
            p1, p2 = diff[idx], diff[idx + 1]
            op_rate = float(r1 - p1 * (r2 - r1) / (p2 - p1))
            op_bhp = self.ipr_pressure(op_rate)
            error = abs(self.ipr_pressure(op_rate) - self.vlp_pressure(op_rate, whp))
            return op_rate, op_bhp, error, "operating_point_found", (
                f"Operating point: {op_rate:.0f} stb/d at {op_bhp:.0f} psi BHP, WHP {whp:.0f} psi."
            )

        if np.all(diff > 0):
            # IPR above VLP — reservoir can deliver more than tubing lifts at all scanned rates
            op_rate = float(rates[-1])
            op_bhp = self.ipr_pressure(op_rate)
            error = float(diff[-1])
            return (
                op_rate,
                op_bhp,
                error,
                "rate_limited_by_vlp",
                "No intersection in range: VLP exceeds IPR at all rates. "
                "Tubing may be too small, WHP too high, or rate range too low. "
                f"Try larger tubing ID or lower WHP.",
            )

        if np.all(diff < 0):
            op_rate = float(rates[0])
            op_bhp = self.ipr_pressure(op_rate)
            error = float(abs(diff[0]))
            return (
                op_rate,
                op_bhp,
                error,
                "ipr_limited",
                "No intersection in range: IPR exceeds VLP at all rates. "
                "Well could produce more — increase rate range or check if choke/WHP is limiting.",
            )

        op_rate = float(rates[len(rates) // 2])
        op_bhp = self.ipr_pressure(op_rate)
        error = abs(self.ipr_pressure(op_rate) - self.vlp_pressure(op_rate, whp))
        return op_rate, op_bhp, error, "no_operating_point", "Could not identify a stable operating point."

    def solve_operating_point(
        self,
        whp_psi: float | None = None,
        rate_guess: float = 1500.0,
        geometry: WellGeometry | None = None,
    ) -> NodalResult:
        """Find rate where IPR and VLP intersect."""
        whp = whp_psi if whp_psi is not None else self.well_geometry.wellhead_pressure_psi
        q_max = max(self.aof_rate() * 1.2, 3000.0)
        rates = np.linspace(100, q_max, 50)
        ipr_p = [self.ipr_pressure(float(r)) for r in rates]
        vlp_p = [self.vlp_pressure(float(r), whp, geometry) for r in rates]

        op_rate, op_bhp, error, status, message = self._classify_intersection(rates, ipr_p, vlp_p, whp)

        return NodalResult(
            rates_stb_d=rates.tolist(),
            ipr_pressures_psi=ipr_p,
            vlp_pressures_psi=vlp_p,
            operating_rate_stb_d=op_rate,
            operating_bhp_psi=op_bhp,
            operating_whp_psi=whp,
            convergence_error=error,
            status=status,
            message=message,
            aof_stb_d=self.aof_rate(),
        )

    def _copy_geometry(self) -> WellGeometry:
        segs = [
            type(s)(
                md_top_ft=s.md_top_ft,
                md_bottom_ft=s.md_bottom_ft,
                tvd_top_ft=s.tvd_top_ft,
                tvd_bottom_ft=s.tvd_bottom_ft,
                inner_diameter_in=s.inner_diameter_in,
                roughness_ft=s.roughness_ft,
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

    def _parameter_label(self, parameter: str, value: float) -> str:
        labels = {
            "tubing_id": f"ID {value:.3f} in",
            "choke_size": f"Choke {value:.0f}/64 in",
            "whp": f"WHP {value:.0f} psi",
            "gor": f"GOR {value:.0f} scf/stb",
            "water_cut": f"WC {value * 100:.0f}%",
        }
        return labels.get(parameter, f"{parameter}={value}")

    def _fluid_copy(self) -> FluidModel:
        props = FluidProperties(**{f.name: getattr(self.fluid.props, f.name) for f in fields(self.fluid.props)})
        return FluidModel(props)

    def sensitivity(
        self,
        parameter: str,
        values: list[float],
        base_whp: float | None = None,
        include_vlp_curves: bool = True,
    ) -> SensitivityResult:
        """Run nodal sensitivity with optional VLP curve overlay per parameter value."""
        whp_base = base_whp or self.well_geometry.wellhead_pressure_psi
        nodal_base = self.solve_operating_point(whp_psi=whp_base)
        curves: list[SensitivityCurve] = []
        diagnostics: list[str] = []

        for val in values:
            geo = self._copy_geometry()
            whp = whp_base
            fluid = self._fluid_copy()

            if parameter == "choke_size":
                geo.choke_size_64_in = val
            elif parameter == "whp":
                whp = val
            elif parameter == "tubing_id":
                for seg in geo.segments:
                    seg.inner_diameter_in = val
            elif parameter == "gor":
                fluid.props.gor_scf_stb = val
            elif parameter == "water_cut":
                fluid.props.water_cut = val

            analyzer = NodalAnalyzer(
                fluid,
                geo,
                self.reservoir_pressure,
                self.pi,
                self.ipr_model,
                self.flow_correlation,
            )
            nodal = analyzer.solve_operating_point(whp_psi=whp, geometry=geo)
            curves.append(
                SensitivityCurve(
                    parameter=parameter,
                    value=val,
                    label=self._parameter_label(parameter, val),
                    rates_stb_d=nodal.rates_stb_d if include_vlp_curves else [],
                    vlp_pressures_psi=nodal.vlp_pressures_psi if include_vlp_curves else [],
                    operating_rate_stb_d=nodal.operating_rate_stb_d,
                    operating_bhp_psi=nodal.operating_bhp_psi,
                    status=nodal.status,
                    message=nodal.message,
                )
            )
            diagnostics.append(f"{self._parameter_label(parameter, val)}: {nodal.message}")

        return SensitivityResult(
            parameter=parameter,
            ipr_rates_stb_d=nodal_base.rates_stb_d,
            ipr_pressures_psi=nodal_base.ipr_pressures_psi,
            curves=curves,
            diagnostics=diagnostics,
        )

    def sensitivity_to_dict(self, result: SensitivityResult) -> dict[str, Any]:
        return {
            "parameter": result.parameter,
            "ipr_rates_stb_d": result.ipr_rates_stb_d,
            "ipr_pressures_psi": result.ipr_pressures_psi,
            "curves": [
                {
                    "parameter": c.parameter,
                    "value": c.value,
                    "label": c.label,
                    "rates_stb_d": c.rates_stb_d,
                    "vlp_pressures_psi": c.vlp_pressures_psi,
                    "operating_rate_stb_d": c.operating_rate_stb_d,
                    "operating_bhp_psi": c.operating_bhp_psi,
                    "status": c.status,
                    "message": c.message,
                }
                for c in result.curves
            ],
            "diagnostics": result.diagnostics,
        }
