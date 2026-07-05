"""Triaxial integrity checks."""

from __future__ import annotations

import math


def biaxial_collapse_factor(axial_klbf: float, yield_psi: float, od: float, id_: float) -> float:
    area = (math.pi / 4) * (od * od - id_ * id_)
    fy = 0.875 * yield_psi * area / 1000
    if axial_klbf <= 0 or fy <= 0:
        return 1.0
    f = axial_klbf / fy
    if f >= 1:
        return 0.0
    return max(math.sqrt(1 - 0.75 * f * f) - 0.5 * f, 0)


def biaxial_burst_factor(axial_klbf: float, yield_psi: float, od: float, id_: float) -> float:
    area = (math.pi / 4) * (od * od - id_ * id_)
    fy = 0.875 * yield_psi * area / 1000
    if axial_klbf >= 0 or fy <= 0:
        return 1.0
    f = abs(axial_klbf) / fy
    if f >= 1:
        return 0.0
    return max(math.sqrt(1 - 0.75 * f * f) - 0.5 * f, 0)


def api_triaxial_check(
    axial_klbf: float,
    p_int: float,
    p_ext: float,
    ratings: dict,
    conn_limits: dict,
    sf: dict,
) -> dict:
    area = (math.pi / 4) * (ratings["od"] ** 2 - ratings["id"] ** 2)
    diff_p = p_int - p_ext
    fa = axial_klbf * 1000
    fy = 0.875 * ratings["yield_psi"] * area

    burst_base = min(ratings["burst"], conn_limits["burst"])
    collapse_base = min(ratings["collapse"], conn_limits["collapse"])
    burst_biax = biaxial_burst_factor(axial_klbf, ratings["yield_psi"], ratings["od"], ratings["id"])
    collapse_biax = biaxial_collapse_factor(axial_klbf, ratings["yield_psi"], ratings["od"], ratings["id"])
    burst_avail = burst_base * burst_biax
    collapse_avail = collapse_base * collapse_biax

    burst_req = max(diff_p, 0) * sf.get("burst", 1.1)
    collapse_req = max(-diff_p, 0) * sf.get("collapse", 1.0)
    burst_util = burst_req / burst_avail if burst_avail > 0 else 0
    collapse_util = collapse_req / collapse_avail if collapse_avail > 0 else 0

    tension_avail = min(ratings["tension"], conn_limits["tension"])
    comp_avail = min(ratings.get("compression", ratings["tension"]), conn_limits["compression"])
    tension_req = max(axial_klbf, 0) * sf.get("tension", 1.2)
    comp_req = max(-axial_klbf, 0) * sf.get("tension", 1.2)
    tension_util = tension_req / tension_avail if tension_avail > 0 else 0
    comp_util = comp_req / comp_avail if comp_avail > 0 else 0

    fe = math.sqrt(max(0, fa * fa - 0.75 * diff_p * diff_p * area * area))
    tri_allowable = fy / sf.get("triaxial", 1.25)
    tri_util = fe / tri_allowable if tri_allowable > 0 else 0

    util = max(burst_util, collapse_util, tension_util, comp_util, tri_util)
    mode = "Triaxial"
    if util == burst_util and burst_util > 0:
        mode = "Burst"
    elif util == collapse_util and collapse_util > 0:
        mode = "Collapse"
    elif util == tension_util and tension_util > 0:
        mode = "Tension"
    elif util == comp_util and comp_util > 0:
        mode = "Compression"

    return {
        "util": util,
        "mode": mode,
        "burst_util": burst_util,
        "collapse_util": collapse_util,
        "tension_util": tension_util,
        "comp_util": comp_util,
        "axial_util": max(tension_util, comp_util),
        "tri_util": tri_util,
        "burst_req": burst_req,
        "collapse_req": collapse_req,
        "tension_req": tension_req,
        "comp_req": comp_req,
        "tri_req": fe,
        "burst_avail": burst_avail,
        "collapse_avail": collapse_avail,
        "tension_avail": tension_avail,
        "comp_avail": comp_avail,
        "tri_avail": tri_allowable,
    }


def triaxial_check(
    axial_klbf: float,
    p_int: float,
    p_ext: float,
    ratings: dict,
    sf: dict,
) -> dict:
    area = (math.pi / 4) * (ratings["od"] ** 2 - ratings["id"] ** 2)
    diff_p = p_int - p_ext
    fa = axial_klbf * 1000
    fy = 0.875 * ratings["yield_psi"] * area

    burst_avail = ratings["burst"] * biaxial_burst_factor(axial_klbf, ratings["yield_psi"], ratings["od"], ratings["id"])
    collapse_avail = ratings["collapse"] * biaxial_collapse_factor(axial_klbf, ratings["yield_psi"], ratings["od"], ratings["id"])

    burst_req = max(diff_p, 0) * sf.get("burst", 1.1)
    collapse_req = max(-diff_p, 0) * sf.get("collapse", 1.0)
    tension_req = max(axial_klbf, 0) * 1000 * sf.get("tension", 1.2)
    comp_req = max(-axial_klbf, 0) * 1000 * sf.get("tension", 1.2)

    burst_util = burst_req / burst_avail if burst_avail > 0 else 0
    collapse_util = collapse_req / collapse_avail if collapse_avail > 0 else 0
    tension_avail = ratings["tension"] * 1000 / sf.get("tension", 1.2)
    tension_util = tension_req / (ratings["tension"] * 1000) if ratings["tension"] > 0 else 0
    comp_util = comp_req / (ratings["compression"] * 1000) if ratings["compression"] > 0 else 0

    fe = math.sqrt(max(0, fa * fa - 0.75 * diff_p * diff_p * area * area))
    tri_util = (fe / fy) * sf.get("triaxial", 1.25) if fy > 0 else 0

    util = max(burst_util, collapse_util, tension_util, comp_util, tri_util)
    mode = "Burst"
    if collapse_util >= util:
        mode = "Collapse"
    if tension_util >= util:
        mode = "Tension"
    if comp_util >= util:
        mode = "Compression"
    if tri_util >= util:
        mode = "Triaxial"

    return {
        "util": util,
        "mode": mode,
        "burst_util": burst_util,
        "collapse_util": collapse_util,
        "axial_util": max(tension_util, comp_util),
        "tri_util": tri_util,
        "burst_avail": burst_avail,
        "collapse_avail": collapse_avail,
        "burst_req": burst_req,
        "collapse_req": collapse_req,
        "tension_req": tension_req,
        "tension_avail": ratings["tension"] * 1000,
        "comp_req": comp_req,
        "comp_avail": ratings["compression"] * 1000,
        "tri_req": fe * sf.get("triaxial", 1.25),
        "tri_avail": fy,
    }
