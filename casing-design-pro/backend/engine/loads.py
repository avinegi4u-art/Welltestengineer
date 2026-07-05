"""Load generation — pressures, axial forces, surge/swab, thermal."""

from __future__ import annotations

import math
from typing import Any

from engine.geometry import POISSON_STEEL, STEEL_ALPHA, inner_area, outer_area, pipe_id_from_weight

DEG = math.pi / 180

THERMAL_MODE_FOR_SCENARIO: dict[str, str] = {
    "thermalCirculation": "circulation",
    "thermalShutin": "shutin",
    "thermalProduction": "production",
    "thermalInjection": "injection",
}

ALL_SCENARIOS = [
    "production", "cementing", "pressureTest", "kick", "evacuation", "stimulation",
    "running", "surge", "swab", "packerSet", "annulusIntegrity",
    "thermalCirculation", "thermalShutin", "thermalProduction", "thermalInjection",
    "tubingMovement",
]


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
    if not inp.get("probDesignEnabled"):
        return 1.0, 1.0
    pp_mult = 1.0 + (inp.get("ppUncertaintyPct", 5) / 100.0)
    fg_mult = 1.0 - (inp.get("fgUncertaintyPct", 5) / 100.0)
    return pp_mult, fg_mult


def surge_swab_margin_ppg(inp: dict, is_surge: bool) -> float:
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


def wear_at_depth(tvd: float, string_id: str, pipe_wear: float | None, wear_profiles: dict, default_wear: float) -> float:
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
    od: float,
    id_: float,
    p_int: float,
    p_ext: float,
    ref_p_int: float,
    ref_p_ext: float,
    nu: float = POISSON_STEEL,
    free_length_ft: float = 1000,
) -> float:
    d_pi = p_int - ref_p_int
    d_pe = p_ext - ref_p_ext
    factor = (2 * nu) / (1 - nu)
    force_lbf = -factor * (d_pi * inner_area(id_) - d_pe * outer_area(od))
    length_scale = min(max(free_length_ft, 1) / 1000, 1.5)
    return (force_lbf / 1000) * length_scale


def buoyed_weight_klbf(od: float, id_: float, length_ft: float, fluid_ppg: float, wt_ppf: float | None) -> float:
    air_lbf_per_ft = wt_ppf if wt_ppf is not None else (0.7854 * (od * od - id_ * id_) * 0.283)
    buoyancy_factor = max(1 - (fluid_ppg / 65.5), 0.12)
    return max(air_lbf_per_ft * length_ft * buoyancy_factor / 1000, 0)


def fluid_segments_for(string_id: str, state: dict) -> list[dict]:
    segments = state.get("fluidSegments") or {}
    return segments.get(string_id, [])


def column_pressure_psi(tvd: float, string: dict, profiles: list[dict], state: dict) -> float:
    segs = fluid_segments_for(string["id"], state)
    if not segs:
        mw = string.get("fluidInt") or interpolate_profile(profiles, tvd, "mwInt")
        return hydrostatic_psi(mw, tvd)
    p = 0.0
    for seg in sorted(segs, key=lambda s: s["top"]):
        if tvd <= seg["top"]:
            break
        from_ = seg["top"]
        to = min(seg["bottom"], tvd)
        length = max(to - from_, 0)
        if length > 0:
            p += hydrostatic_psi(seg["ppg"], length)
    return p


def offshore_external_psi(tvd: float, mw_ext: float, inp: dict) -> float:
    sw = inp.get("seawaterPpg", 8.6)
    wd = inp.get("waterDepth", 0)
    if wd <= 0:
        return hydrostatic_psi(mw_ext, tvd)
    mudline_tvd = wd + (inp.get("rigElev", 0))
    if tvd <= mudline_tvd:
        return hydrostatic_psi(sw, tvd)
    return hydrostatic_psi(sw, mudline_tvd) + hydrostatic_psi(mw_ext, tvd - mudline_tvd)


def external_zone(tvd: float, string: dict) -> str:
    toc = string.get("toc", string.get("top", 0))
    return "open" if tvd < toc else "cemented"


def thermal_settings(inp: dict, state: dict) -> dict[str, Any]:
    th = state.get("thermal") or {}
    return {
        "enabled": th.get("enabled", True) and inp.get("thermalEnabled", True) is not False,
        "mode": th.get("mode") or inp.get("thermalMode") or "circulation",
        "time_hours": th.get("timeHours", inp.get("thermalTimeHours", 12)),
        "circulating_temp_f": th.get("circulatingTempF", inp.get("thermalCircTempF", 120)),
        "production_temp_f": th.get("productionTempF", inp.get("thermalProdTempF", 285)),
        "injection_temp_f": th.get("injectionTempF", inp.get("thermalInjTempF", 95)),
        "relax_depth_ft": th.get("relaxDepthFt", inp.get("thermalRelaxFt", 5000)),
        "warmback_hours": th.get("warmbackHours", inp.get("thermalWarmbackHrs", 48)),
        "poisson": th.get("poisson", inp.get("thermalPoisson", POISSON_STEEL)),
    }


def temperature_at_depth(
    tvd: float,
    inp: dict,
    state: dict,
    scenario_key: str | None = None,
    profiles: list[dict] | None = None,
) -> float:
    profiles = profiles if profiles is not None else state.get("profiles", [])
    geo = interpolate_profile(profiles, tvd, "temp")
    th = thermal_settings(inp, state)
    mode = th["mode"]
    if scenario_key and scenario_key in THERMAL_MODE_FOR_SCENARIO:
        mode = THERMAL_MODE_FOR_SCENARIO[scenario_key]
    elif scenario_key == "tubingMovement":
        mode = "production"
    if (
        not th["enabled"]
        and scenario_key not in THERMAL_MODE_FOR_SCENARIO
        and scenario_key != "tubingMovement"
    ):
        return geo
    relax = max(th["relax_depth_ft"], 500)
    frac = 1 - math.exp(-tvd / relax)
    if mode == "circulation":
        t_circ = th["circulating_temp_f"]
        return t_circ + (geo - t_circ) * frac
    if mode == "shutin":
        t_circ = th["circulating_temp_f"]
        warm = min(1.0, th["time_hours"] / max(th["warmback_hours"], 1))
        t_circ_prof = t_circ + (geo - t_circ) * frac
        return t_circ_prof + warm * (geo - t_circ_prof)
    if mode == "production":
        t_bh = th["production_temp_f"]
        max_shoe = max([s.get("shoe", 0) for s in state.get("strings", [])] + [tvd, 1])
        prod_frac = min(1.0, tvd / (max_shoe * 0.88))
        return geo + prod_frac * (t_bh - geo)
    if mode == "injection":
        t_inj = th["injection_temp_f"]
        return t_inj + (geo - t_inj) * frac * 0.35
    return geo


def apb_pressure_from_temperature(initial_psi: float, initial_temp_f: float, current_temp_f: float) -> float:
    t1 = (initial_temp_f or 70) + 459.67
    t2 = (current_temp_f or 70) + 459.67
    if t1 <= 0:
        return initial_psi
    return max(initial_psi * (t2 / t1), 0)


def annulus_at_depth(tvd: float, string_id: str, state: dict) -> dict | None:
    for ann in state.get("annuli") or []:
        if (
            (ann.get("innerStringId") == string_id or ann.get("outerStringId") == string_id)
            and tvd >= ann.get("topTvd", 0)
            and tvd <= ann.get("bottomTvd", 99999)
        ):
            return ann
    return None


def annulus_pressure_psi(annulus: dict, tvd: float, inp: dict, state: dict, scenario_key: str | None) -> float:
    temp = temperature_at_depth(tvd, inp, state, scenario_key)
    p0 = annulus.get("initialPressurePsi", annulus.get("trappedPressurePsi", 0))
    t0 = annulus.get("initialTempF", inp.get("refTempF", 70))
    p = apb_pressure_from_temperature(p0, t0, temp)
    compliance = annulus.get("complianceBblPerPsi", 0)
    if compliance > 0 and annulus.get("volumeBbl", 0) > 0:
        d_t = temp - t0
        beta = annulus.get("fluidExpPerF", 0.00045)
        d_v = annulus["volumeBbl"] * beta * d_t
        p += d_v / compliance
    return p


def annulus_external_pressure_at_depth(
    tvd: float,
    string: dict,
    inp: dict,
    state: dict,
    scenario_key: str | None,
) -> float | None:
    ann = annulus_at_depth(tvd, string["id"], state)
    if not ann or ann.get("sealed") is False:
        return None
    if string["id"] == ann.get("innerStringId"):
        return annulus_pressure_psi(ann, tvd, inp, state, scenario_key)
    return None


def packers_on_string(string_id: str, state: dict) -> list[dict]:
    return [p for p in state.get("packers") or [] if p.get("stringId") == string_id]


def packer_near_depth(tvd: float, string_id: str, state: dict) -> dict | None:
    tol = 300
    for p in packers_on_string(string_id, state):
        if abs(p.get("depth", 0) - tvd) <= tol:
            return p
    return None


def external_pressure_at_depth(
    tvd: float,
    string: dict,
    scenario_key: str,
    inp: dict,
    profiles: list[dict],
    state: dict,
) -> float:
    pp_mult, _ = probabilistic_factors(inp)
    pp = interpolate_profile(profiles, tvd, "pp") * pp_mult
    mw_e = string.get("fluidExt") or interpolate_profile(profiles, tvd, "mwExt")
    p_pp = hydrostatic_psi(pp, tvd)
    zone = external_zone(tvd, string)

    if scenario_key == "evacuation":
        p_ext = p_pp * 0.9 if zone == "cemented" else offshore_external_psi(tvd, mw_e, inp) * 0.15
    elif zone == "open":
        p_ext = offshore_external_psi(tvd, mw_e, inp)
    elif scenario_key == "production":
        p_ext = p_pp * 0.65
    elif scenario_key == "stimulation":
        p_ext = p_pp * 0.75
    else:
        p_ext = p_pp

    if inp.get("apbEnabled") and string.get("apbSealed") and zone == "cemented":
        apb = string.get("apbPsi", inp.get("apbDefaultPsi", 0))
        p_ext = max(p_ext, apb)

    ann_p = annulus_external_pressure_at_depth(tvd, string, inp, state, scenario_key)
    if ann_p is not None:
        p_ext = max(p_ext, ann_p)

    if scenario_key in ("annulusIntegrity", "tubingMovement"):
        pk = packer_near_depth(tvd, string["id"], state)
        ann_psi = (pk or {}).get("annulusPsi", string.get("apbPsi", inp.get("apbDefaultPsi", 0)))
        p_ext = max(p_ext, ann_psi, p_pp * 0.7)
    return p_ext


def internal_pressure_at_depth(
    tvd: float,
    string: dict,
    scenario_key: str,
    inp: dict,
    profiles: list[dict],
    state: dict,
    cement_schedule: list[dict],
) -> float:
    pp_mult, fg_mult = probabilistic_factors(inp)
    fg = interpolate_profile(profiles, tvd, "fg") * fg_mult
    pp = interpolate_profile(profiles, tvd, "pp") * pp_mult
    p_fg = hydrostatic_psi(fg, tvd)
    p_mw = column_pressure_psi(tvd, string, profiles, state)
    p_pp = hydrostatic_psi(pp, tvd)

    if scenario_key == "kick":
        return min(p_fg * 0.92, p_mw + 250)
    if scenario_key == "pressureTest":
        return min(p_fg * 0.85, p_mw * 1.2)
    if scenario_key == "stimulation":
        return p_fg * 0.95
    if scenario_key == "evacuation":
        return 0.0
    if scenario_key == "production":
        return max(p_mw, p_pp * 0.95)
    if scenario_key == "cementing":
        mw = string.get("fluidInt") or interpolate_profile(profiles, tvd, "mwInt")
        return cementing_pressure_at_depth(tvd, cement_schedule, mw)
    if scenario_key == "running":
        return p_mw
    if scenario_key == "surge":
        mw_base = p_mw / max(0.052 * max(tvd, 1), 1)
        return hydrostatic_psi(mw_base + surge_swab_margin_ppg(inp, True), tvd)
    if scenario_key == "swab":
        mw_base = p_mw / max(0.052 * max(tvd, 1), 1)
        return hydrostatic_psi(max(mw_base + surge_swab_margin_ppg(inp, False), 0.1), tvd)
    if scenario_key == "packerSet":
        return max(p_mw * 1.15, p_pp * 0.9)
    if scenario_key == "annulusIntegrity":
        return p_mw
    if scenario_key in ("thermalCirculation", "thermalShutin"):
        return p_mw
    if scenario_key == "thermalProduction":
        return max(p_mw, p_pp * 0.98)
    if scenario_key == "thermalInjection":
        return p_mw * 1.08
    if scenario_key == "tubingMovement":
        return max(p_mw, p_pp * 0.95)
    return p_mw


def reference_pressures_at_install(
    tvd: float,
    string: dict,
    inp: dict,
    profiles: list[dict],
    state: dict,
) -> dict[str, float]:
    return {
        "p_int": column_pressure_psi(tvd, string, profiles, state),
        "p_ext": offshore_external_psi(
            tvd,
            string.get("fluidExt") or interpolate_profile(profiles, tvd, "mwExt"),
            inp,
        ),
    }


def constrained_length_ft(tvd: float, string: dict, state: dict) -> float:
    packers = [p for p in packers_on_string(string["id"], state) if p.get("depth", 0) <= tvd]
    anchor = packers[-1]["depth"] if packers else string.get("toc", string.get("top", 0))
    return max(tvd - anchor, 0)


def piston_force_klbf(
    od: float,
    id_: float,
    p_int: float,
    p_ext: float,
    ref_p_int: float,
    ref_p_ext: float,
    seal_id_in: float | None,
) -> float:
    d_pi = p_int - ref_p_int
    d_pe = p_ext - ref_p_ext
    a_seal = inner_area(seal_id_in if seal_id_in is not None else id_)
    a_metal = outer_area(od) - inner_area(id_)
    return (d_pi * a_seal - d_pe * a_metal) / 1000


def packer_movement_summary(
    packer: dict,
    inp: dict,
    state: dict,
    profiles: list[dict],
    cement_schedule: list[dict],
    scenario_key: str | None,
    catalog: dict[str, dict],
) -> dict[str, float] | None:
    string = next((s for s in state.get("strings", []) if s.get("id") == packer.get("stringId")), None)
    if not string:
        return None
    pipe = catalog.get(string.get("pipeId"))
    if not pipe:
        return None
    id_ = pipe_id_from_weight(pipe["od"], pipe["wt"])
    depth = packer.get("depth", 0)
    temp = temperature_at_depth(depth, inp, state, scenario_key, profiles)
    ref_t = inp.get("refTempF", 70)
    delta_t = temp - ref_t
    ref_p = reference_pressures_at_install(depth, string, inp, profiles, state)
    p_int = internal_pressure_at_depth(depth, string, scenario_key or "production", inp, profiles, state, cement_schedule)
    p_ext = external_pressure_at_depth(depth, string, scenario_key or "production", inp, profiles, state)
    nu = thermal_settings(inp, state)["poisson"]
    free_len = constrained_length_ft(depth, string, state)
    balloon = ballooning_axial_klbf(pipe["od"], id_, p_int, p_ext, ref_p["p_int"], ref_p["p_ext"], nu, free_len)
    piston = piston_force_klbf(pipe["od"], id_, p_int, p_ext, ref_p["p_int"], ref_p["p_ext"], packer.get("sealIdIn", id_))
    return {"delta_t": delta_t, "balloon": balloon, "piston": piston}


def string_interaction_axial_klbf(
    tvd: float,
    string: dict,
    inp: dict,
    state: dict,
    profiles: list[dict],
    cement_schedule: list[dict],
    scenario_key: str | None,
    catalog: dict[str, dict],
) -> float:
    xfer = 0.0
    for pk in state.get("packers") or []:
        if abs(pk.get("depth", 0) - tvd) > 300:
            continue
        inner = next((s for s in state.get("strings", []) if s.get("id") == pk.get("stringId")), None)
        if not inner:
            continue
        ann = annulus_at_depth(tvd, inner["id"], state)
        if not ann or ann.get("outerStringId") != string["id"]:
            continue
        summary = packer_movement_summary(pk, inp, state, profiles, cement_schedule, scenario_key, catalog)
        if summary:
            xfer += pk.get("setDownKlbf", 0) + summary["balloon"] + summary["piston"]
    return xfer


def build_survey_derived(survey: list[dict]) -> list[dict]:
    pts = sorted(survey, key=lambda p: p["md"])
    if len(pts) < 2:
        return []
    derived = [{**pts[0], "tvd": 0.0, "dls": 0.0}]
    for i in range(1, len(pts)):
        p0, p1 = pts[i - 1], pts[i]
        d_md = max(p1["md"] - p0["md"], 1)
        inc0, inc1 = p0["inc"] * DEG, p1["inc"] * DEG
        azi0, azi1 = p0["azi"] * DEG, p1["azi"] * DEG
        d_tvd = d_md * (math.cos(inc0) + math.cos(inc1)) / 2
        dogleg = math.acos(
            min(
                1.0,
                max(
                    -1.0,
                    math.cos(inc1 - inc0) - math.sin(inc0) * math.sin(inc1) * (1 - math.cos(azi1 - azi0)),
                ),
            )
        )
        dls = (dogleg / DEG) * (100 / d_md)
        derived.append({**p1, "tvd": derived[-1]["tvd"] + d_tvd, "dls": dls})
    return derived


def md_at_tvd(tvd: float, survey: list[dict]) -> float:
    derived = build_survey_derived(survey)
    if not derived:
        return tvd
    if tvd <= derived[0]["tvd"]:
        return derived[0]["md"]
    if tvd >= derived[-1]["tvd"]:
        return derived[-1]["md"]
    for i in range(1, len(derived)):
        if tvd <= derived[i]["tvd"]:
            f = (tvd - derived[i - 1]["tvd"]) / (derived[i]["tvd"] - derived[i - 1]["tvd"])
            return derived[i - 1]["md"] + f * (derived[i]["md"] - derived[i - 1]["md"])
    return tvd


def survey_at_tvd(tvd: float, survey: list[dict]) -> dict[str, float]:
    derived = build_survey_derived(survey)
    if not derived:
        return {"inc": 0.0, "azi": 0.0, "tvd": tvd, "dls": 0.0}
    md = md_at_tvd(tvd, survey)
    if md <= derived[0]["md"]:
        return {k: float(derived[0].get(k, 0)) for k in ("inc", "azi", "tvd", "dls")}
    if md >= derived[-1]["md"]:
        return {k: float(derived[-1].get(k, 0)) for k in ("inc", "azi", "tvd", "dls")}
    for i in range(1, len(derived)):
        if md <= derived[i]["md"]:
            f = (md - derived[i - 1]["md"]) / (derived[i]["md"] - derived[i - 1]["md"])
            return {
                "inc": derived[i - 1]["inc"] + f * (derived[i]["inc"] - derived[i - 1]["inc"]),
                "azi": derived[i - 1]["azi"] + f * (derived[i]["azi"] - derived[i - 1]["azi"]),
                "tvd": derived[i - 1]["tvd"] + f * (derived[i]["tvd"] - derived[i - 1]["tvd"]),
                "dls": derived[i - 1]["dls"] + f * (derived[i]["dls"] - derived[i - 1]["dls"]),
            }
    return {"inc": 0.0, "azi": 0.0, "tvd": tvd, "dls": 0.0}


def running_drag_klbf(
    tvd: float,
    string: dict,
    inp: dict,
    pipe: dict,
    survey: list[dict],
) -> float:
    id_ = pipe_id_from_weight(pipe["od"], pipe["wt"])
    below = max(string.get("shoe", 0) - tvd, 0)
    weight = buoyed_weight_klbf(pipe["od"], id_, below, string.get("fluidInt", 8.6), pipe.get("wt"))
    inc = survey_at_tvd(tvd, survey)["inc"]
    mu = inp.get("dragCoeff", 0.25)
    return weight * mu * math.sin(inc * DEG)


def axial_force_at_depth(
    tvd: float,
    string: dict,
    inp: dict,
    state: dict,
    profiles: list[dict],
    cement_schedule: list[dict],
    scenario_key: str,
    catalog: dict[str, dict],
) -> float:
    pipe = catalog.get(string.get("pipeId"))
    if not pipe:
        return 0.0
    id_ = pipe_id_from_weight(pipe["od"], pipe["wt"])
    below = max(string.get("shoe", 0) - tvd, 0)
    axial = buoyed_weight_klbf(pipe["od"], id_, below, string.get("fluidInt", 8.6), pipe.get("wt"))

    if string.get("type") == "liner":
        hang = string.get("hangOffKlbf", axial * 1.15)
        if tvd <= string.get("top", 0) + 50:
            axial += hang
        elif tvd < string.get("top", 0) + 500:
            axial += hang * (1 - (tvd - string.get("top", 0)) / 500)
    if string.get("type") == "tieback":
        axial += string.get("preTensionKlbf", 150)

    if tvd <= string.get("top", 0) + 100:
        axial += string.get("hangerLoadKlbf", 0)

    temp = temperature_at_depth(tvd, inp, state, scenario_key, profiles)
    ref_t = inp.get("refTempF", 70)
    d_t = temp - ref_t
    constrained = 1.0 if tvd <= (string.get("toc", string.get("top", 0))) else 0.35
    axial += thermal_axial_klbf(pipe["od"], id_, d_t) * constrained

    ref_p = reference_pressures_at_install(tvd, string, inp, profiles, state)
    p_int = internal_pressure_at_depth(tvd, string, scenario_key, inp, profiles, state, cement_schedule)
    p_ext = external_pressure_at_depth(tvd, string, scenario_key, inp, profiles, state)
    nu = thermal_settings(inp, state)["poisson"]
    free_len = constrained_length_ft(tvd, string, state)
    th = thermal_settings(inp, state)
    if scenario_key == "tubingMovement" or scenario_key in THERMAL_MODE_FOR_SCENARIO or th["enabled"]:
        axial += ballooning_axial_klbf(pipe["od"], id_, p_int, p_ext, ref_p["p_int"], ref_p["p_ext"], nu, free_len)

    if scenario_key == "running":
        overpull = inp.get("runningOverpullKlbf", 50)
        drag = running_drag_klbf(tvd, string, inp, pipe, state.get("survey") or [])
        shock = inp.get("shockFactor", 1.15)
        axial = (axial + overpull + drag) * shock

    pk = packer_near_depth(tvd, string["id"], state)
    if pk:
        summary = packer_movement_summary(pk, inp, state, profiles, cement_schedule, scenario_key, catalog)
        if scenario_key == "packerSet":
            axial += pk.get("setDownKlbf", 0)
        elif scenario_key == "tubingMovement" and summary:
            axial += pk.get("setDownKlbf", 0) + summary["balloon"] + summary["piston"]
        elif scenario_key in ("production", "annulusIntegrity", "thermalProduction") and summary:
            axial += pk.get("setDownKlbf", 0) * 0.5 + summary["balloon"] * 0.5

    axial += string_interaction_axial_klbf(
        tvd, string, inp, state, profiles, cement_schedule, scenario_key, catalog
    )
    return axial


def scenarios_for_load_generation(inp: dict, state: dict) -> list[str]:
    thermal_keys = set(THERMAL_MODE_FOR_SCENARIO.keys())
    active = [k for k in ALL_SCENARIOS if k not in thermal_keys]
    if thermal_settings(inp, state)["enabled"]:
        active.extend(THERMAL_MODE_FOR_SCENARIO.keys())
    if state.get("packers"):
        active.append("tubingMovement")
    seen: set[str] = set()
    out: list[str] = []
    for key in active:
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


# Backward-compatible alias used by older tests / montecarlo path
def internal_pressure(
    tvd: float,
    scenario: str,
    pp: float,
    fg: float,
    p_mw: float,
    inp: dict,
    cement_schedule: list,
) -> float:
    string = {"id": "legacy", "fluidInt": p_mw / max(0.052 * max(tvd, 1), 1)}
    profiles = [{"tvd": 0, "pp": pp, "fg": fg, "mwInt": string["fluidInt"], "mwExt": 8.6, "temp": 70}]
    state: dict[str, Any] = {"profiles": profiles, "strings": [string]}
    return internal_pressure_at_depth(tvd, string, scenario, inp, profiles, state, cement_schedule)
