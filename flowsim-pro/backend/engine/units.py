"""Unit conversion utilities for petroleum engineering calculations."""

from __future__ import annotations

from enum import Enum
from typing import Final

PSI_TO_PA: Final[float] = 6894.757
PA_TO_PSI: Final[float] = 1.0 / PSI_TO_PA
FT_TO_M: Final[float] = 0.3048
M_TO_FT: Final[float] = 1.0 / FT_TO_M
IN_TO_M: Final[float] = 0.0254
M_TO_IN: Final[float] = 1.0 / IN_TO_M
BBL_TO_M3: Final[float] = 0.158987
M3_TO_BBL: Final[float] = 1.0 / BBL_TO_M3
SCF_TO_M3: Final[float] = 0.0283168
M3_TO_SCF: Final[float] = 1.0 / SCF_TO_M3
CP_TO_PAS: Final[float] = 0.001
RANKINE_OFFSET: Final[float] = 459.67


class PressureUnit(str, Enum):
    PSI = "psi"
    PA = "pa"
    KPA = "kpa"
    BAR = "bar"


class LengthUnit(str, Enum):
    FT = "ft"
    M = "m"
    IN = "in"


class RateUnit(str, Enum):
    STB_D = "stb/d"
    M3_D = "m3/d"
    MSCF_D = "mscf/d"


def pressure_to_psi(value: float, unit: PressureUnit) -> float:
    """Convert pressure to psi."""
    if unit == PressureUnit.PSI:
        return value
    if unit == PressureUnit.PA:
        return value * PA_TO_PSI
    if unit == PressureUnit.KPA:
        return value * 1000.0 * PA_TO_PSI
    if unit == PressureUnit.BAR:
        return value * 1e5 * PA_TO_PSI
    raise ValueError(f"Unsupported pressure unit: {unit}")


def length_to_ft(value: float, unit: LengthUnit) -> float:
    """Convert length to feet."""
    if unit == LengthUnit.FT:
        return value
    if unit == LengthUnit.M:
        return value * M_TO_FT
    if unit == LengthUnit.IN:
        return value / 12.0
    raise ValueError(f"Unsupported length unit: {unit}")


def diameter_in_to_ft(diameter_in: float) -> float:
    """Convert pipe inner diameter from inches to feet."""
    return diameter_in / 12.0


def api_to_sg(api_gravity: float) -> float:
    """Convert API gravity to oil specific gravity (water=1)."""
    return 141.5 / (api_gravity + 131.5)


def f_to_rankine(temp_f: float) -> float:
    return temp_f + RANKINE_OFFSET


def rankine_to_f(temp_r: float) -> float:
    return temp_r - RANKINE_OFFSET


def validate_positive(value: float, name: str, min_value: float = 0.0) -> None:
    if value <= min_value:
        raise ValueError(f"{name} must be greater than {min_value}, got {value}")


def validate_range(value: float, name: str, low: float, high: float) -> None:
    if not low <= value <= high:
        raise ValueError(f"{name} must be between {low} and {high}, got {value}")
