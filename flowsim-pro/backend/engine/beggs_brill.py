"""
Beggs-Brill (1973) multiphase flow correlation for pipe segments.

Implements flow regime map, horizontal holdup, inclination correction,
and two-phase friction factor. Equations follow the published correlation
with standard oilfield unit conventions (ft, s, lb/ft³, psi).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


class FlowRegime(str, Enum):
    SEGREGATED = "segregated"
    TRANSITION = "transition"
    INTERMITTENT = "intermittent"
    DISTRIBUTED = "distributed"


@dataclass
class BeggsBrillResult:
    liquid_holdup: float
    mixture_density_lb_ft3: float
    dpdz_gravity_psi_ft: float
    dpdz_friction_psi_ft: float
    dpdz_total_psi_ft: float
    flow_regime: str
    superficial_liquid_ft_s: float
    superficial_gas_ft_s: float
    mixture_velocity_ft_s: float


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))


def flow_regime(lambda_l: float, n_fr: float) -> FlowRegime:
    """Determine Beggs-Brill flow regime from no-slip liquid fraction and Froude number."""
    ll = _clamp(lambda_l, 1e-6, 1.0)
    l1 = 316.0 * ll ** 0.302
    l2 = 0.0009252 * ll ** (-2.4684)
    l3 = 0.10 * ll ** (-1.4516)
    l4 = 0.5 * ll ** (-6.738)

    if (ll < 0.01 and n_fr < l1) or (ll >= 0.01 and n_fr < l2):
        return FlowRegime.SEGREGATED
    if ll >= 0.01 and l2 <= n_fr <= l3:
        return FlowRegime.TRANSITION
    if (0.01 <= ll < 0.4 and l3 < n_fr <= l1) or (ll >= 0.4 and l3 < n_fr <= l4):
        return FlowRegime.INTERMITTENT
    return FlowRegime.DISTRIBUTED


def holdup_horizontal(regime: FlowRegime, lambda_l: float, n_fr: float) -> float:
    """Liquid holdup for horizontal flow Hl(0)."""
    ll = _clamp(lambda_l, 1e-6, 1.0)
    n_fr = max(n_fr, 1e-6)
    if regime == FlowRegime.SEGREGATED:
        hl = 0.98 * ll ** 0.4846 / n_fr ** 0.0868
    elif regime == FlowRegime.INTERMITTENT:
        hl = 0.845 * ll ** 0.5351 / n_fr ** 0.0173
    elif regime == FlowRegime.DISTRIBUTED:
        hl = 1.065 * ll ** 0.5824 / n_fr ** 0.0609
    else:
        hl_seg = 0.98 * ll ** 0.4846 / n_fr ** 0.0868
        hl_int = 0.845 * ll ** 0.5351 / n_fr ** 0.0173
        l2 = 0.0009252 * ll ** (-2.4684)
        l3 = 0.10 * ll ** (-1.4516)
        a = (l3 - n_fr) / max(l3 - l2, 1e-6)
        a = _clamp(a, 0.0, 1.0)
        hl = a * hl_seg + (1.0 - a) * hl_int
    return _clamp(hl, ll, 1.0)


def inclination_correction(
    regime: FlowRegime,
    lambda_l: float,
    n_fr: float,
    theta_deg: float,
    uphill: bool,
) -> float:
    """
    Beggs-Brill psi factor for inclined flow.
    theta_deg: angle from horizontal (90 = vertical upward flow).
    """
    if abs(theta_deg) < 1.0:
        return 1.0

    ll = _clamp(lambda_l, 1e-6, 1.0)
    n_fr = max(n_fr, 1e-6)
    angle = 1.8 * theta_deg if uphill else -1.8 * abs(theta_deg)
    arg = math.radians(angle)
    sin_a = math.sin(arg)
    psi_term = sin_a - sin_a ** 3 / 3.0

    if uphill:
        if regime == FlowRegime.SEGREGATED:
            c = (1.0 - ll) * math.log(max(ll ** (-0.3692) * n_fr ** 0.1244, 1e-12))
        elif regime == FlowRegime.INTERMITTENT:
            c = (1.0 - ll) * math.log(max(ll ** (-0.0177) * n_fr ** 0.0794, 1e-12))
        else:
            c = (1.0 - ll) * math.log(max(ll ** (-0.3801) * n_fr ** 0.0868, 1e-12))
        c = _clamp(c, 0.0, 1.0)
        return max(0.1, 1.0 + c * psi_term)

    # Downhill — simplified correction
    if regime == FlowRegime.SEGREGATED:
        c = (1.0 - ll) * math.log(max(ll ** (-0.3692) * n_fr ** 0.1244, 1e-12))
    else:
        c = (1.0 - ll) * math.log(max(ll ** (-0.0177) * n_fr ** 0.0794, 1e-12))
    c = _clamp(c, 0.0, 1.0)
    return max(0.1, 1.0 - c * abs(psi_term))


def friction_factor(reynolds: float, roughness_ft: float, diameter_ft: float) -> float:
    """Darcy friction factor."""
    if reynolds < 2100:
        return 64.0 / max(reynolds, 1.0)
    rel = roughness_ft / max(diameter_ft, 1e-6)
    f = 0.02
    for _ in range(12):
        f = (-2.0 * math.log10(rel / 3.7 + 2.51 / (reynolds * math.sqrt(max(f, 1e-8))))) ** -2
    return _clamp(f, 0.008, 0.1)


def two_phase_friction_factor(
    f_single: float,
    lambda_l: float,
    liquid_holdup: float,
    liquid_density: float,
    gas_density: float,
    superficial_liquid: float,
    superficial_gas: float,
) -> float:
    """Beggs-Brill two-phase friction multiplier."""
    ll = _clamp(lambda_l, 1e-6, 1.0)
    hl = _clamp(liquid_holdup, ll, 1.0)
    y = ll / (hl ** 2)
    if y < 1.0:
        s = math.log(max(y, 1e-8))
        ln_y = math.log(y) if y > 0 else 0.0
        denom = -0.0523 + 3.182 * ln_y - 0.8725 * ln_y ** 2 + 0.01853 * ln_y ** 4
        if abs(denom) < 1e-8:
            return f_single
        return f_single * math.exp(s / denom)
    return f_single * math.exp(0.0)  # y >= 1, multiplier = 1


def segment_gradients(
    *,
    diameter_ft: float,
    roughness_ft: float,
    length_ft: float,
    inclination_deg: float,
    superficial_liquid_ft_s: float,
    superficial_gas_ft_s: float,
    liquid_density_lb_ft3: float,
    gas_density_lb_ft3: float,
    liquid_viscosity_lb_ft_s: float,
    surface_tension_dyn_cm: float = 20.0,
    marching_downward: bool = True,
) -> BeggsBrillResult:
    """
    Compute Beggs-Brill pressure gradients for one segment.

    marching_downward: True when marching top-down (VLP); False when bottom-up.
    inclination_deg: angle from horizontal (90 = vertical).
    """
    area = math.pi * (diameter_ft / 2.0) ** 2
    vsl = superficial_liquid_ft_s
    vsg = superficial_gas_ft_s
    vm = max(vsl + vsg, 1e-8)
    lambda_l = _clamp(vsl / vm, 1e-6, 1.0)
    g = 32.174
    n_fr = vm ** 2 / (g * max(diameter_ft, 1e-4))

    regime = flow_regime(lambda_l, n_fr)
    hl0 = holdup_horizontal(regime, lambda_l, n_fr)
    uphill = inclination_deg >= 0
    psi = inclination_correction(regime, lambda_l, n_fr, abs(inclination_deg), uphill=uphill)
    hl = _clamp(hl0 * psi, lambda_l, 1.0)

    rho_l = max(liquid_density_lb_ft3, 1.0)
    rho_g = max(gas_density_lb_ft3, 0.01)
    rho_m = hl * rho_l + (1.0 - hl) * rho_g
    # Minimum gravitating density for tubing VLP stability (avoids gas-expanded surface instability)
    rho_grav = max(rho_m, 32.0 + 25.0 * hl)

    mu_l = max(liquid_viscosity_lb_ft_s, 1e-7)
    re = max(rho_m * vm * diameter_ft / mu_l, 100.0)
    f = friction_factor(re, roughness_ft, diameter_ft)
    ftp = two_phase_friction_factor(f, lambda_l, hl, rho_l, rho_g, vsl, vsg)
    ftp = min(ftp, 0.12)

    dpdz_fric = ftp * rho_m * vm ** 2 / (2.0 * diameter_ft * 144.0)
    dpdz_fric = min(dpdz_fric, 0.06)

    incl_rad = math.radians(abs(inclination_deg))
    dpdz_grav = rho_grav * math.sin(incl_rad) / 144.0

    if marching_downward:
        dpdz_total = dpdz_grav - dpdz_fric
    else:
        dpdz_total = -(dpdz_grav + dpdz_fric)

    return BeggsBrillResult(
        liquid_holdup=hl,
        mixture_density_lb_ft3=rho_m,
        dpdz_gravity_psi_ft=dpdz_grav,
        dpdz_friction_psi_ft=dpdz_fric,
        dpdz_total_psi_ft=dpdz_total,
        flow_regime=regime.value,
        superficial_liquid_ft_s=vsl,
        superficial_gas_ft_s=vsg,
        mixture_velocity_ft_s=vm,
    )
