"""Pipe geometry helpers."""

from __future__ import annotations

import math

K_WEIGHT = (0.7854 * 490) / 144
STEEL_ALPHA = 6.5e-6
POISSON_STEEL = 0.3


def pipe_id_from_weight(od: float, wt_ppf: float) -> float:
    id_sq = od * od - wt_ppf / K_WEIGHT
    if id_sq <= 0:
        return od * 0.85
    return math.sqrt(id_sq)


def wall_thickness(od: float, id_: float) -> float:
    return (od - id_) / 2


def worn_geometry(od: float, wt_ppf: float, wear_pct: float) -> tuple[float, float]:
    id0 = pipe_id_from_weight(od, wt_ppf)
    t = wall_thickness(od, id0)
    wear_in = (wear_pct / 100.0) * t
    id_worn = min(id0 + 2 * wear_in, od * 0.92)
    return od, id_worn


def metal_area(od: float, id_: float) -> float:
    return (math.pi / 4) * (od * od - id_ * id_)


def inner_area(id_: float) -> float:
    return (math.pi / 4) * id_ * id_


def outer_area(od: float) -> float:
    return (math.pi / 4) * od * od
