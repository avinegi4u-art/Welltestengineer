"""Buckling checks — Dawson-Paslay and Euler span."""

from __future__ import annotations

import math

from engine.loads import buoyed_weight_klbf, survey_at_tvd

DEG = math.pi / 180
E_STEEL = 30e6


def buoyed_weight_per_ft_lbf(od: float, id_: float, fluid_ppg: float, wt_ppf: float | None) -> float:
    return buoyed_weight_klbf(od, id_, 1.0, fluid_ppg, wt_ppf) * 1000


def bending_equivalent_axial_klbf(od: float, inc_deg: float, dls: float) -> float:
    if dls <= 0 or inc_deg <= 0:
        return 0.0
    inc = inc_deg * DEG
    return (E_STEEL * od * dls * math.sin(inc)) / (2 * 57300)


def effective_axial_for_triaxial(axial_klbf: float, od: float, inc_deg: float, dls: float) -> float:
    bend = bending_equivalent_axial_klbf(od, inc_deg, dls)
    return axial_klbf + bend if axial_klbf >= 0 else axial_klbf - bend


def dawson_paslay_sinusoidal_klbf(
    od: float,
    id_: float,
    inc_deg: float,
    fluid_ppg: float,
    radial_clearance_in: float,
    wt_ppf: float | None,
) -> float:
    i_moment = (math.pi / 64) * (od**4 - id_**4)
    w = buoyed_weight_per_ft_lbf(od, id_, fluid_ppg, wt_ppf)
    theta = inc_deg * DEG
    r = max(radial_clearance_in or 0.5, 0.125)
    if w <= 0 or math.sin(theta) < 0.001:
        return float("inf")
    return (2 * math.sqrt(E_STEEL * i_moment * w * math.sin(theta) / r)) / 1000


def dawson_paslay_helical_klbf(
    od: float,
    id_: float,
    inc_deg: float,
    fluid_ppg: float,
    radial_clearance_in: float,
    wt_ppf: float | None,
) -> float:
    fs = dawson_paslay_sinusoidal_klbf(od, id_, inc_deg, fluid_ppg, radial_clearance_in, wt_ppf)
    return float("inf") if fs == float("inf") else fs * math.sqrt(2)


def sinusoidal_buckling_klbf(od: float, id_: float, span_ft: float, dls: float = 0) -> float:
    if span_ft <= 0:
        return float("inf")
    i_moment = (math.pi / 64) * (od**4 - id_**4)
    fcr = (math.pi * math.pi * E_STEEL * i_moment) / (span_ft * span_ft) / 1000
    dls_factor = 1 + (dls / 8) ** 2
    return fcr / dls_factor


def buckling_check(
    axial_klbf: float,
    ratings: dict,
    string: dict,
    depth: float,
    inp: dict,
    sf: dict,
    survey: list[dict],
) -> dict:
    sv = survey_at_tvd(depth, survey)
    inc = sv["inc"]
    dls = sv.get("dls", 0) or 0
    comp_klbf = max(-axial_klbf, 0)
    fluid_ppg = string.get("fluidInt", 9)
    r_clear = string.get("radialClearance", 0.5)
    span = min(max(string.get("spanFt", 60), 20), 200)
    wt_ppf = ratings.get("wt")

    if comp_klbf <= 0:
        return {
            "util": 0.0,
            "mode": "Buckling",
            "required": 0.0,
            "available": float("inf"),
            "sin_avail": float("inf"),
            "hel_avail": float("inf"),
            "comp_klbf": 0.0,
            "inc": inc,
            "dls": dls,
            "span": span,
        }

    sf_buck = sf.get("buckling", 1.25)
    sin_avail_dp = dawson_paslay_sinusoidal_klbf(
        ratings["od"], ratings["id"], inc, fluid_ppg, r_clear, wt_ppf
    )
    hel_avail_dp = dawson_paslay_helical_klbf(
        ratings["od"], ratings["id"], inc, fluid_ppg, r_clear, wt_ppf
    )
    sin_avail_euler = sinusoidal_buckling_klbf(ratings["od"], ratings["id"], span, dls)

    if inc > 5:
        sin_avail = sin_avail_dp / sf_buck
        hel_avail = hel_avail_dp / sf_buck
    else:
        sin_avail = min(sin_avail_dp, sin_avail_euler) / sf_buck
        hel_avail = min(hel_avail_dp, sin_avail_euler * math.sqrt(2)) / sf_buck

    sin_util = comp_klbf / sin_avail if sin_avail > 0 and sin_avail < float("inf") else 0.0
    hel_util = comp_klbf / hel_avail if hel_avail > 0 and hel_avail < float("inf") else 0.0

    if hel_util >= sin_util and hel_util > 0:
        return {
            "util": hel_util,
            "mode": "Helical Buckling",
            "required": comp_klbf,
            "available": hel_avail,
            "sin_avail": sin_avail,
            "hel_avail": hel_avail,
            "sin_util": sin_util,
            "hel_util": hel_util,
            "comp_klbf": comp_klbf,
            "inc": inc,
            "dls": dls,
            "span": span,
        }
    return {
        "util": sin_util,
        "mode": "Sinusoidal Buckling",
        "required": comp_klbf,
        "available": sin_avail,
        "sin_avail": sin_avail,
        "hel_avail": hel_avail,
        "sin_util": sin_util,
        "hel_util": hel_util,
        "comp_klbf": comp_klbf,
        "inc": inc,
        "dls": dls,
        "span": span,
    }
