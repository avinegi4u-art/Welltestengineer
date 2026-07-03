"""
Black-oil and simplified compositional fluid property model.

Uses standard petroleum engineering correlations (Standing, Beggs-Robinson)
with transparent, documented equations. Designed for extension with PVT tables.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from engine.units import api_to_sg, validate_positive, validate_range


@dataclass
class FluidProperties:
    """Black-oil fluid definition."""

    model_type: str = "black_oil"  # black_oil | compositional_simplified
    oil_api: float = 35.0
    gas_gravity: float = 0.65
    water_salinity_ppm: float = 50000.0
    gor_scf_stb: float = 800.0
    water_cut: float = 0.10
    bubble_point_psi: float = 2500.0
    reservoir_temp_f: float = 180.0
    pvt_table: list[dict[str, float]] | None = None
    compositional: dict[str, float] | None = None

    def validate(self) -> list[str]:
        warnings: list[str] = []
        try:
            validate_positive(self.oil_api, "oil_api", min_value=5.0)
            validate_positive(self.gas_gravity, "gas_gravity")
            validate_range(self.water_cut, "water_cut", 0.0, 1.0)
            validate_positive(self.gor_scf_stb, "gor_scf_stb")
        except ValueError as exc:
            warnings.append(str(exc))
        if self.water_cut > 0.95:
            warnings.append("Water cut above 95% may reduce correlation accuracy.")
        return warnings


@dataclass
class PhaseState:
    """Multiphase fluid state at given P, T."""

    pressure_psi: float
    temperature_f: float
    oil_rate_stb_d: float
    gas_rate_mscf_d: float
    water_rate_stb_d: float
    liquid_rate_stb_d: float
    total_rate_stb_d: float
    gor_scf_stb: float
    water_cut: float
    oil_fvf: float
    gas_fvf: float
    water_fvf: float
    oil_density_lb_ft3: float
    gas_density_lb_ft3: float
    water_density_lb_ft3: float
    oil_viscosity_cp: float
    gas_viscosity_cp: float
    water_viscosity_cp: float
    mixture_density_lb_ft3: float
    mixture_viscosity_cp: float
    liquid_holdup: float
    gas_void_fraction: float


class FluidModel:
    """Compute black-oil PVT and in-situ multiphase properties."""

    def __init__(self, props: FluidProperties) -> None:
        self.props = props
        self._pvt_df: pd.DataFrame | None = None
        if props.pvt_table:
            self._pvt_df = pd.DataFrame(props.pvt_table).sort_values("pressure_psi")

    def solution_gor(self, pressure_psi: float) -> float:
        """Solution GOR (scf/stb) using linearized bubble-point model."""
        pb = self.props.bubble_point_psi
        rs_max = self.props.gor_scf_stb
        p = max(pressure_psi, 14.7)
        if p >= pb:
            return rs_max
        return rs_max * (p / pb) ** 1.2

    def oil_formation_volume_factor(
        self, pressure_psi: float, temperature_f: float, rs: float
    ) -> float:
        """Standing correlation for Bo (rb/stb)."""
        if self._pvt_df is not None:
            return float(
                np.interp(
                    pressure_psi,
                    self._pvt_df["pressure_psi"].values,
                    self._pvt_df["oil_fvf"].values,
                )
            )
        gamma_o = api_to_sg(self.props.oil_api)
        gamma_g = self.props.gas_gravity
        t_rankine = temperature_f + 459.67
        bo = (
            0.9759
            + 0.00012 * (rs * (gamma_g / gamma_o) ** 0.5 + 1.25 * temperature_f) ** 1.2
        )
        if pressure_psi < self.props.bubble_point_psi:
            co = 1.0e-5  # simplified oil compressibility 1/psi
            bo *= np.exp(co * (self.props.bubble_point_psi - pressure_psi))
        return float(bo)

    def oil_viscosity(self, pressure_psi: float, temperature_f: float, rs: float) -> float:
        """Beggs-Robinson dead oil + live oil correction."""
        if self._pvt_df is not None and "oil_viscosity_cp" in self._pvt_df.columns:
            return float(
                np.interp(
                    pressure_psi,
                    self._pvt_df["pressure_psi"].values,
                    self._pvt_df["oil_viscosity_cp"].values,
                )
            )
        x = 10 ** (3.0324 - 0.02023 * self.props.oil_api)
        mu_od = 10 ** x * temperature_f ** (-1.163)  # dead oil cp
        a = 10.715 * (rs + 100) ** (-0.515)
        b = 5.44 * (rs + 150) ** (-0.338)
        mu_o = a * mu_od ** b
        if pressure_psi > self.props.bubble_point_psi:
            mu_o *= 1.0 + 1.0e-4 * (pressure_psi - self.props.bubble_point_psi)
        return float(max(mu_o, 0.1))

    def gas_formation_volume_factor(
        self, pressure_psi: float, temperature_f: float, z_factor: float = 0.9
    ) -> float:
        """Bg (rb/scf) from real gas law."""
        t_rankine = temperature_f + 459.67
        bg = 0.02827 * z_factor * t_rankine / pressure_psi
        return float(bg)

    def gas_density(self, pressure_psi: float, temperature_f: float, z_factor: float = 0.9) -> float:
        """Gas density lb/ft3."""
        mw = self.props.gas_gravity * 28.97
        t_rankine = temperature_f + 459.67
        rho = pressure_psi * mw / (z_factor * 10.73 * t_rankine)
        return float(rho)

    def oil_density(self, pressure_psi: float, temperature_f: float, rs: float, bo: float) -> float:
        """Oil density at P,T."""
        gamma_o = api_to_sg(self.props.oil_api)
        gamma_g = self.props.gas_gravity
        rho_sc = 62.4 * gamma_o + 0.0136 * gamma_g * rs
        return float(rho_sc / bo)

    def water_density(self) -> float:
        """Brine density lb/ft3."""
        salinity = self.props.water_salinity_ppm
        return float(62.4 * (1.0 + 0.0000007 * salinity))

    def water_viscosity(self, temperature_f: float) -> float:
        """Simple water viscosity correlation."""
        return float(max(0.2, 1.0 - 0.0003 * (temperature_f - 60.0)))

    def z_factor(self, pressure_psi: float, temperature_f: float) -> float:
        """Simplified gas Z-factor."""
        t_rankine = temperature_f + 459.67
        ppc = 677.0 + 15.0 * self.props.gas_gravity - 37.5 * self.props.gas_gravity**2
        tpc = 168.0 + 325.0 * self.props.gas_gravity - 12.5 * self.props.gas_gravity**2
        ppr = pressure_psi / ppc
        tpr = t_rankine / tpc
        z = 1.0 - 0.03 * ppr / tpr
        return float(max(0.5, min(z, 1.2)))

    def compute_rates(
        self, liquid_rate_stb_d: float, gor_scf_stb: float | None = None, wc: float | None = None
    ) -> tuple[float, float, float]:
        """Split total liquid into oil/water and compute gas rate."""
        wc = self.props.water_cut if wc is None else wc
        gor = self.props.gor_scf_stb if gor_scf_stb is None else gor_scf_stb
        water_rate = liquid_rate_stb_d * wc
        oil_rate = liquid_rate_stb_d * (1.0 - wc)
        gas_rate_mscf = oil_rate * gor / 1000.0
        return oil_rate, gas_rate_mscf, water_rate

    def no_slip_holdup(
        self,
        oil_rate: float,
        gas_rate_mscf: float,
        water_rate: float,
        pressure_psi: float,
        temperature_f: float,
    ) -> float:
        """Liquid volume fraction without slip (lambda_l)."""
        rs = self.solution_gor(pressure_psi)
        bo = self.oil_formation_volume_factor(pressure_psi, temperature_f, rs)
        bw = 1.02
        bg = self.gas_formation_volume_factor(pressure_psi, temperature_f, self.z_factor(pressure_psi, temperature_f))
        qo = oil_rate * bo
        qw = water_rate * bw
        qg = gas_rate_mscf * 1000.0 * bg
        ql = qo + qw
        total = ql + qg
        if total <= 0:
            return 1.0
        return float(ql / total)

    def mixture_properties(
        self,
        pressure_psi: float,
        temperature_f: float,
        liquid_rate_stb_d: float,
        inclination_deg: float = 90.0,
    ) -> PhaseState:
        """Compute full multiphase state at given conditions."""
        pressure_psi = max(pressure_psi, 14.7)
        oil_rate, gas_rate, water_rate = self.compute_rates(liquid_rate_stb_d)
        rs = self.solution_gor(pressure_psi)
        bo = self.oil_formation_volume_factor(pressure_psi, temperature_f, rs)
        bw = 1.02
        bg = self.gas_formation_volume_factor(pressure_psi, temperature_f, self.z_factor(pressure_psi, temperature_f))
        mu_o = self.oil_viscosity(pressure_psi, temperature_f, rs)
        mu_w = self.water_viscosity(temperature_f)
        mu_g = 0.02
        rho_o = self.oil_density(pressure_psi, temperature_f, rs, bo)
        rho_w = self.water_density()
        rho_g = self.gas_density(pressure_psi, temperature_f, self.z_factor(pressure_psi, temperature_f))

        lambda_l = self.no_slip_holdup(oil_rate, gas_rate, water_rate, pressure_psi, temperature_f)
        # Simplified drift-flux holdup with inclination correction (Hagedorn-Brown inspired bounds)
        hl = min(0.99, max(0.25, lambda_l + 0.25 * (1.0 - lambda_l) * np.sin(np.radians(inclination_deg))))
        hg = 1.0 - hl

        rho_m = hl * (rho_o * (1 - self.props.water_cut) + rho_w * self.props.water_cut) + hg * rho_g
        mu_l = mu_o * (1 - self.props.water_cut) + mu_w * self.props.water_cut
        mu_m = hl * mu_l + hg * mu_g

        return PhaseState(
            pressure_psi=pressure_psi,
            temperature_f=temperature_f,
            oil_rate_stb_d=oil_rate,
            gas_rate_mscf_d=gas_rate,
            water_rate_stb_d=water_rate,
            liquid_rate_stb_d=liquid_rate_stb_d,
            total_rate_stb_d=liquid_rate_stb_d + gas_rate * 1000.0 / max(self.props.gor_scf_stb, 1.0),
            gor_scf_stb=self.props.gor_scf_stb,
            water_cut=self.props.water_cut,
            oil_fvf=bo,
            gas_fvf=bg,
            water_fvf=bw,
            oil_density_lb_ft3=rho_o,
            gas_density_lb_ft3=rho_g,
            water_density_lb_ft3=rho_w,
            oil_viscosity_cp=mu_o,
            gas_viscosity_cp=mu_g,
            water_viscosity_cp=mu_w,
            mixture_density_lb_ft3=rho_m,
            mixture_viscosity_cp=mu_m,
            liquid_holdup=hl,
            gas_void_fraction=hg,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_type": self.props.model_type,
            "oil_api": self.props.oil_api,
            "gas_gravity": self.props.gas_gravity,
            "water_salinity_ppm": self.props.water_salinity_ppm,
            "gor_scf_stb": self.props.gor_scf_stb,
            "water_cut": self.props.water_cut,
            "bubble_point_psi": self.props.bubble_point_psi,
            "reservoir_temp_f": self.props.reservoir_temp_f,
        }
