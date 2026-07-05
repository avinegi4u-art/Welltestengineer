"""Load generation — surge/swab, cementing, probabilistic envelopes."""

from __future__ import annotations

import math
from typing import Any

from engine.geometry import POISSON_STEEL, STEEL_ALPHA, inner_area, outer_area, pipe_id_from_weight


def hydrostatic_psi(ppg: float, tvd: float) -> float:
    return ppg * 0.052 * max(tvd, 0)


def interpolate_profile(profiles: list[dict], depth: float, field: str) -> float:
    if not profiles:
        return 0.0
    sorted_p = sorted(profiles, key=lambda p: p["tvd"])
    if depth <= sorted_p[0]["tvd"]:
        return float(sorted_p[0][field])
    if depth >= sorted_p[-1]["tvd"]:
        return float(sorted_p[-1][field])
    for i in range(1, len(sorted_p)):
        if depth <= sorted_p[i]["tvd"]:
            a, b = sorted_p[i - 1], sorted_p[i]
            f = (depth - a["tvd"]) / (b["tvd"] - a["tvd"])
            return float(a[field]) + f * (float(b[field]) - float(a[field]))
    return float(sorted_p[0][field])


def probabilistic_factors(inp: dict) -> tuple[float, float]:
    """Return (pp_mult, fg_mult) for P90 pore / P10 fracture style screening."""
    if not inp.get("probDesignEnabled"):
        return 1.0, 1.0
    pp_mult = 1.0 + (inp.get("ppUncertaintyPct", 5) / 100.0)
    fg_mult = 1.0 - (inp.get("fgUncertaintyPct", 5) / 100.0)
    return pp_mult, fg_mult


def surge_swab_margin_ppg(inp: dict, is_surge: bool) -> float:
    """Simplified API RP 13D-style equivalent MW change from pipe speed."""
    speed = inp.get("pipeSpeedFtMin", 90)
    pv = inp.get("mudPlasticVisc", 25)
    base = 0.15 + 0.00035 * pv * speed / 100.0
    return base if is_surge else -base


def cementing_pressure_at_depth(tvd: float, schedule: list[dict], default_mw: float) -> float:
    if not schedule:
        return hydrostatic_psi(default_mw * 1.12, tvd)
    p_max = 0.0
    for stage in schedule:
        top = stage.get("topTvd", 0)
        bot = stage.get("bottomTvd", 99999)
        if top <= tvd <= bot:
            if stage.get("pressurePsi"):
                p_max = max(p_max, float(stage["pressurePsi"]))
            ppg = stage.get("densityPpg", default_mw)
            p_max = max(p_max, hydrostatic_psi(ppg, tvd))
    return p_max if p_max > 0 else hydrostatic_psi(default_mw * 1.12, tvd)


def wear_at_depth(tvd: float, string_id: str, pipe_wear: float, wear_profiles: dict, default_wear: float) -> float:
    segs = wear_profiles.get(string_id, [])
    if not segs:
        return pipe_wear if pipe_wear is not None else default_wear
    for seg in segs:
        if seg.get("top", 0) <= tvd <= seg.get("bottom", 99999):
            return float(seg.get("wearPct", default_wear))
    return pipe_wear if pipe_wear is not None else default_wear


def thermal_axial_klbf(od: float, id_: float, delta_t: float) -> float:
    area = (math.pi / 4) * (od * od - id_ * id_)
    e = 30e6
    return -(STEEL_ALPHA * delta_t * e * area) / 1000


def ballooning_axial_klbf(
    od: float, id_: float, p_int: float, p_ext: float,
    ref_p_int: float, ref_p_ext: float, nu: float = POISSON_STEEL, free_length_ft: float = 1000,
) -> float:
    d_pi = p_int - ref_p_int
    d_pe = p_ext - ref_p_ext
    factor = (2 * nu) / (1 - nu)
    force_lbf = -factor * (d_pi * inner_area(id_) - d_pe * outer_area(od))
    length_scale = min(max(free_length_ft, 1) / 1000, 1.5)
    return (force_lbf / 1000) * length_scale


def internal_pressure(
    tvd: float, scenario: str, pp: float, fg: float, p_mw: float, inp: dict, cement_schedule: list,
) -> float:
    pp_mult, fg_mult = probabilistic_factors(inp)
    p_pp = hydrostatic_psi(pp * pp_mult, tvd)
    p_fg = hydrostatic_psi(fg * fg_mult, tvd)

    if scenario == "kick":
        return min(p_fg * 0.92, p_mw + 250)
    if scenario == "pressureTest":
        return min(p_fg * 0.85, p_mw * 1.2)
    if scenario == "stimulation":
        return p_fg * 0.95
    if scenario == "evacuation":
        return 0.0
    if scenario == "production":
        return max(p_mw, p_pp * 0.95)
    if scenario == "cementing":
        return cementing_pressure_at_depth(tvd, cement_schedule, p_mw / max(0.052 * max(tvd, 1), 1))
    if scenario == "running":
        return p_mw
    if scenario == "surge":
        margin = surge_swab_margin_ppg(inp, True)
        mw = p_mw / max(0.052 * max(tvd, 1), 1) + margin
        return hydrostatic_psi(mw, tvd)
    if scenario == "swab":
        margin = surge_swab_margin_ppg(inp, False)
        mw = max(p_mw / max(0.052 * max(tvd, 1), 1) + margin, 0.1)
        return hydrostatic_psi(mw, tvd)
    if scenario == "packerSet":
        return max(p_mw * 1.15, p_pp * 0.9)
    return p_mw
