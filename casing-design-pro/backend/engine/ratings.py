"""API 5CT / ISO 10400 pipe ratings."""

from __future__ import annotations

import math

from engine.geometry import metal_area, pipe_id_from_weight, wall_thickness, worn_geometry

GRADES: dict[str, dict[str, float]] = {
    "H40": {"yield": 40000, "uts": 60000},
    "J55": {"yield": 55000, "uts": 75000},
    "K55": {"yield": 55000, "uts": 95000},
    "N80": {"yield": 80000, "uts": 100000},
    "L80": {"yield": 80000, "uts": 95000},
    "C90": {"yield": 90000, "uts": 100000},
    "T95": {"yield": 95000, "uts": 105000},
    "P110": {"yield": 110000, "uts": 125000},
    "Q125": {"yield": 125000, "uts": 135000},
}

TEMP_DERATE: dict[str, list[tuple[float, float]]] = {
    "K55": [(250, 1), (300, 1), (350, 0.99), (400, 0.96), (450, 0.93)],
    "L80": [(250, 1), (300, 0.97), (350, 0.94), (400, 0.91), (450, 0.87)],
    "N80": [(250, 1), (300, 0.97), (350, 0.94), (400, 0.91), (450, 0.87)],
    "P110": [(250, 1), (300, 0.96), (350, 0.93), (400, 0.9), (450, 0.86)],
    "Q125": [(250, 1), (300, 0.95), (350, 0.92), (400, 0.89), (450, 0.85)],
}

SOUR_DERATE: list[tuple[float, float]] = [
    (0.0, 1.0),
    (0.05, 1.0),
    (0.1, 0.95),
    (0.5, 0.85),
    (1.0, 0.75),
    (3.0, 0.65),
]


def temp_derating_factor(grade: str, temp_f: float) -> float:
    pts = TEMP_DERATE.get(grade, TEMP_DERATE["L80"])
    if temp_f <= pts[0][0]:
        return 1.0
    for i in range(1, len(pts)):
        if temp_f <= pts[i][0]:
            t0, f0 = pts[i - 1]
            t1, f1 = pts[i]
            return f0 + ((f1 - f0) * (temp_f - t0)) / (t1 - t0)
    return pts[-1][1]


def sour_derating_factor(h2s_psi: float) -> float:
    if h2s_psi <= 0:
        return 1.0
    for i in range(1, len(SOUR_DERATE)):
        if h2s_psi <= SOUR_DERATE[i][0]:
            p0, f0 = SOUR_DERATE[i - 1]
            p1, f1 = SOUR_DERATE[i]
            return f0 + ((f1 - f0) * (h2s_psi - p0)) / (p1 - p0)
    return SOUR_DERATE[-1][1]


def barlow_burst(od: float, id_: float, yield_psi: float, design_code: str = "api") -> float:
    t = wall_thickness(od, id_)
    factor = 0.875 if design_code == "api" else 1.0
    return factor * ((2 * yield_psi * t) / od)


def api_collapse_pressure(od: float, id_: float, yield_psi: float, design_code: str = "api") -> float:
    t = wall_thickness(od, id_)
    d_t = od / t
    yp = yield_psi
    e = 30e6
    ype = (2 * yp) / e
    a = 2.8762 + 0.10679e-5 * yp + 0.21301e-10 * yp * yp - 0.53132e-16 * yp**3
    b = 0.026233 + 0.50636e-6 * yp
    c = -465.93 + 0.030867 * yp - 0.10483e-7 * yp * yp + 0.36989e-13 * yp**3
    f = 46.95e6 * (3 * b / (2 + b)) ** 3 * ype ** (b / (2 + b))
    g = f * ype
    pyp = (2 * yp * (d_t - 1)) / (d_t * d_t)
    pp = yp * (c / d_t - g)
    pe = 46.95e6 / (d_t * (d_t - 1) ** 2)
    threshold = (yp / e) * (3 * b / (2 + b)) ** 3 * ype ** (b / (2 + b)) * (2 + b) / (3 * b)
    if d_t < threshold:
        pc = pyp
    elif d_t < 15:
        pc = min(pyp, max(pp, 0))
    elif d_t < 25:
        pc = min(pp, pe) if pp > 0 else pe
    else:
        pc = pe
    factor = 0.875 if design_code == "api" else 0.9
    return factor * max(pc, 0)


def body_yield_tension_klbf(od: float, id_: float, yield_psi: float, design_code: str = "api") -> float:
    area = metal_area(od, id_)
    factor = 0.875 if design_code == "api" else 0.9
    return (factor * yield_psi * area) / 1000


def calc_pipe_ratings(
    od: float,
    wt: float,
    grade: str,
    temp_f: float = 200.0,
    derate_on: bool = True,
    wear_pct: float = 0.0,
    design_code: str = "api",
    h2s_psi: float = 0.0,
) -> dict:
    g = GRADES.get(grade, GRADES["L80"])
    od_w, id_w = worn_geometry(od, wt, wear_pct)
    derate = 1.0
    if derate_on:
        derate = temp_derating_factor(grade, temp_f)
    derate *= sour_derating_factor(h2s_psi)
    y = g["yield"] * derate
    tension = body_yield_tension_klbf(od_w, id_w, y, design_code)
    return {
        "od": od_w,
        "id": id_w,
        "wt": wt,
        "grade": grade,
        "yield_psi": y,
        "burst": barlow_burst(od_w, id_w, y, design_code),
        "collapse": api_collapse_pressure(od_w, id_w, y, design_code),
        "tension": tension,
        "compression": tension,
        "wear_pct": wear_pct,
    }
