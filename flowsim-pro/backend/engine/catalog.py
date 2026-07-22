"""
Standard tubing and flowline catalogs for selection studies.

IDs are representative industry values (nominal OD / weight → drift/ID).
Not affiliated with any manufacturer catalog.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TubingSize:
    label: str
    od_in: float
    weight_lb_ft: float
    inner_diameter_in: float
    roughness_ft: float = 0.00015


@dataclass(frozen=True)
class PipeSize:
    label: str
    nominal_in: float
    schedule: str
    inner_diameter_in: float
    roughness_ft: float = 0.00015


# Common production tubing sizes (approx. drift / ID)
TUBING_CATALOG: list[TubingSize] = [
    TubingSize("2-3/8\" 4.7#", 2.375, 4.7, 1.995),
    TubingSize("2-7/8\" 6.5#", 2.875, 6.5, 2.441),
    TubingSize("3-1/2\" 9.3#", 3.5, 9.3, 2.992),
    TubingSize("4\" 9.5#", 4.0, 9.5, 3.476),
    TubingSize("4-1/2\" 12.6#", 4.5, 12.6, 3.958),
    TubingSize("5\" 15.0#", 5.0, 15.0, 4.408),
    TubingSize("5-1/2\" 17.0#", 5.5, 17.0, 4.892),
    TubingSize("7\" 26.0#", 7.0, 26.0, 6.276),
]


# Common flowline / surface line sizes (approx. ID for std weight / Sch 40)
FLOWLINE_CATALOG: list[PipeSize] = [
    PipeSize('2" Sch40', 2.0, "40", 2.067),
    PipeSize('3" Sch40', 3.0, "40", 3.068),
    PipeSize('4" Sch40', 4.0, "40", 4.026),
    PipeSize('6" Sch40', 6.0, "40", 6.065),
    PipeSize('8" Sch40', 8.0, "40", 7.981),
    PipeSize('10" Sch40', 10.0, "40", 10.020),
    PipeSize('12" Sch40', 12.0, "40", 11.938),
]


def tubing_by_id(inner_diameter_in: float, tol: float = 0.02) -> TubingSize | None:
    for t in TUBING_CATALOG:
        if abs(t.inner_diameter_in - inner_diameter_in) <= tol:
            return t
    return None


def pipe_by_id(inner_diameter_in: float, tol: float = 0.05) -> PipeSize | None:
    for p in FLOWLINE_CATALOG:
        if abs(p.inner_diameter_in - inner_diameter_in) <= tol:
            return p
    return None


def catalog_to_dict() -> dict:
    return {
        "tubing": [
            {
                "label": t.label,
                "od_in": t.od_in,
                "weight_lb_ft": t.weight_lb_ft,
                "inner_diameter_in": t.inner_diameter_in,
                "roughness_ft": t.roughness_ft,
            }
            for t in TUBING_CATALOG
        ],
        "flowline": [
            {
                "label": p.label,
                "nominal_in": p.nominal_in,
                "schedule": p.schedule,
                "inner_diameter_in": p.inner_diameter_in,
                "roughness_ft": p.roughness_ft,
            }
            for p in FLOWLINE_CATALOG
        ],
    }
