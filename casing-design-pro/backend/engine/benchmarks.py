"""Engine regression benchmarks — parity with JS ENGINE_BENCHMARKS."""

from __future__ import annotations

import math
from typing import Any, Callable

from engine.buckling import (
    buckling_check,
    dawson_paslay_sinusoidal_klbf,
)
from engine.connections import connection_limits, iso_ellipse_burst_allowance, iso_ellipse_tension_allowance
from engine.geometry import pipe_id_from_weight, wall_thickness
from engine.loads import (
    apb_pressure_from_temperature,
    ballooning_axial_klbf,
    cementing_pressure_at_depth,
    hydrostatic_psi,
    offshore_external_psi,
    piston_force_klbf,
    probabilistic_factors,
    surge_swab_margin_ppg,
    temperature_at_depth,
    thermal_axial_klbf,
    wear_at_depth,
)
from engine.montecarlo import percentile
from engine.ratings import (
    api_collapse_pressure,
    barlow_burst,
    body_yield_tension_klbf,
    calc_pipe_ratings,
    sour_derating_factor,
    temp_derating_factor,
)
from engine.triaxial import api_triaxial_check, biaxial_burst_factor, biaxial_collapse_factor
from engine.vme import interpolate_burst_at_axial

BenchmarkCase = tuple[str, str, Callable[[], float], float, float, str]


def _run_case(case: BenchmarkCase) -> dict[str, Any]:
    cid, name, fn, expected, tol_pct, unit = case
    got = fn()
    err_pct = abs(got - expected) / max(abs(expected), 1e-9) * 100
    return {
        "id": cid,
        "name": name,
        "got": got,
        "expected": expected,
        "err_pct": err_pct,
        "pass": err_pct <= tol_pct,
        "tol_pct": tol_pct,
        "unit": unit,
    }


def benchmark_cases() -> list[BenchmarkCase]:
    id_7_23 = pipe_id_from_weight(7, 23)
    id_7_29 = pipe_id_from_weight(7, 29)
    id_9_625 = pipe_id_from_weight(9.625, 53.5)
    id_13_375 = pipe_id_from_weight(13.375, 68)

    def triaxial_burst_util() -> float:
        r = calc_pipe_ratings(7, 29, "N80", temp_f=200, derate_on=False, wear_pct=0)
        c = connection_limits(r, "BTC")
        return api_triaxial_check(
            50, 4000, 1000, r, c, {"burst": 1.1, "collapse": 1, "tension": 1.2, "triaxial": 1.25, "buckling": 1.3}
        )["burst_util"]

    def buckling_tension_zero() -> float:
        r = calc_pipe_ratings(9.625, 53.5, "P110", temp_f=200, derate_on=False, wear_pct=0)
        s = {"fluidInt": 9, "spanFt": 60, "radialClearance": 0.5}
        return buckling_check(250, r, s, 5000, {}, {"buckling": 1.3}, [])["util"]

    def vme_burst_half_tension() -> float:
        r = calc_pipe_ratings(9.625, 53.5, "P110", temp_f=200, derate_on=False, wear_pct=0)
        c = connection_limits(r, "BTC")
        return iso_ellipse_burst_allowance(c["vme"]["conn_burst0"], c["vme"]["conn_tension0"], c["vme"]["conn_tension0"] * 0.5)

    def vme_tension_half_burst() -> float:
        r = calc_pipe_ratings(7, 29, "N80", temp_f=200, derate_on=False, wear_pct=0)
        c = connection_limits(r, "VAM TOP")
        return iso_ellipse_tension_allowance(c["vme"]["conn_tension0"], c["vme"]["conn_burst0"], c["vme"]["conn_burst0"] * 0.5)

    def wear_delta_burst() -> float:
        pristine = calc_pipe_ratings(7, 29, "N80", temp_f=200, derate_on=False, wear_pct=0)["burst"]
        worn = calc_pipe_ratings(7, 29, "N80", temp_f=200, derate_on=False, wear_pct=10)["burst"]
        return pristine - worn

    def triaxial_fe_fy() -> float:
        r = calc_pipe_ratings(7, 29, "N80", temp_f=200, derate_on=False, wear_pct=0)
        area = (math.pi / 4) * (r["od"] ** 2 - r["id"] ** 2)
        fa = 200 * 1000
        diff_p = 3000
        fe = math.sqrt(max(0, fa * fa - 0.75 * diff_p * diff_p * area * area))
        fy = 0.875 * r["yield_psi"] * area
        return fe / fy

    def vam_top_tension() -> float:
        r = calc_pipe_ratings(9.625, 53.5, "L80", temp_f=200, derate_on=False, wear_pct=0)
        return connection_limits(r, "VAM TOP")["tension"]

    def thermal_circ_8k() -> float:
        inp = {"thermalEnabled": True, "thermalMode": "circulation", "thermalCircTempF": 120, "thermalRelaxFt": 5000, "refTempF": 70}
        st = {
            "thermal": {"enabled": True, "mode": "circulation", "circulatingTempF": 120, "relaxDepthFt": 5000},
            "profiles": [{"tvd": 0, "temp": 70}, {"tvd": 11000, "temp": 220}],
            "strings": [],
        }
        return temperature_at_depth(8000, inp, st, "thermalCirculation")

    def cement_5k() -> float:
        sched = [{"topTvd": 0, "bottomTvd": 11000, "densityPpg": 15.2}]
        return cementing_pressure_at_depth(5000, sched, 10)

    def wear_depth_12() -> float:
        profiles: dict[str, list] = {"s1": [{"top": 6000, "bottom": 11000, "wearPct": 12}]}
        return wear_at_depth(7000, "s1", 0, profiles, 0)

    def mc_p50() -> float:
        return percentile([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0], 50)

    return [
        ("barlow_7_23_n80", "7\" 23# N80 Barlow burst (API)", lambda: barlow_burst(7, id_7_23, 80000), 6444, 2, "psi"),
        ("collapse_7_23_n80", "7\" 23# N80 API collapse", lambda: api_collapse_pressure(7, id_7_23, 80000), 4402, 3, "psi"),
        ("tension_9_625_53_p110", "9.625\" 53.5# P110 body tension", lambda: body_yield_tension_klbf(9.625, id_9_625, 110000), 1513, 3, "klbf"),
        ("hydrostatic_10ppg_10000", "10 ppg hydrostatic @ 10,000 ft", lambda: hydrostatic_psi(10, 10000), 5200, 0.5, "psi"),
        ("biaxial_burst_comp", "Biaxial burst factor (compression)", lambda: biaxial_burst_factor(-200, 80000, 7, id_7_29), 0.789, 3, "ratio"),
        ("triaxial_pure_burst", "Triaxial burst-dominated check", triaxial_burst_util, 0.40, 8, "util"),
        ("dawson_paslay_deviated", "Dawson-Paslay sinusoidal (32° inc)", lambda: dawson_paslay_sinusoidal_klbf(9.625, id_9_625, 32, 10.5, 0.5, 53.5), 963, 5, "klbf"),
        ("buckling_compression_only", "Buckling ignores tension", buckling_tension_zero, 0, 1, "util"),
        ("pipe_id_formula", "Pipe ID from weight (7\" 29#)", lambda: pipe_id_from_weight(7, 29), 6.176, 1, "in"),
        ("thermal_contraction", "Thermal axial (ΔT = −150°F)", lambda: abs(thermal_axial_klbf(7, id_7_29, -150)), 249, 5, "klbf"),
        ("wall_thickness_7_29", "Wall thickness 7\" 29#", lambda: wall_thickness(7, id_7_29), 0.412, 2, "in"),
        ("barlow_9_625_p110", "9.625\" 53.5# P110 Barlow burst", lambda: barlow_burst(9.625, id_9_625, 110000), 11031, 2, "psi"),
        ("collapse_13_375_l80", "13.375\" 68# L80 API collapse", lambda: api_collapse_pressure(13.375, id_13_375, 80000), 2229, 3, "psi"),
        ("vme_burst_half_tension", "VME burst @ 50% conn tension", vme_burst_half_tension, 9553, 2, "psi"),
        ("vme_tension_under_pressure", "VME tension @ 50% conn burst ΔP", vme_tension_half_burst, 372, 5, "klbf"),
        ("biaxial_collapse_tension", "Biaxial collapse factor (tension)", lambda: biaxial_collapse_factor(300, 80000, 7, id_7_29), 0.652, 3, "ratio"),
        ("temp_derate_p110_400f", "P110 temp derating @ 400°F", lambda: temp_derating_factor("P110", 400), 0.9, 2, "ratio"),
        ("wear_reduces_burst", "Wear reduces burst rating (10% vs 0%)", wear_delta_burst, 824, 8, "psi"),
        ("hydrostatic_12ppg_8000", "12 ppg hydrostatic @ 8,000 ft", lambda: hydrostatic_psi(12, 8000), 4992, 0.5, "psi"),
        ("triaxial_fe_fy", "Triaxial Fe/Fy (burst + tension)", triaxial_fe_fy, 0.33, 5, "ratio"),
        ("vam_top_conn_tension", "VAM TOP connection tension cap", vam_top_tension, 792, 3, "klbf"),
        ("offshore_external_mudline", "Offshore external @ 3,000 ft (WD=1500)", lambda: offshore_external_psi(3000, 9.0, {"waterDepth": 1500, "rigElev": 75, "seawaterPpg": 8.6}), 1371, 3, "psi"),
        ("thermal_expansion_200f", "Thermal axial expansion (ΔT = +200°F, 7\" 29#)", lambda: abs(thermal_axial_klbf(7, id_7_29, 200)), 332, 5, "klbf"),
        ("apb_temp_ratio", "APB pressure ratio (T₂/T₁, 70→220°F)", lambda: apb_pressure_from_temperature(1200, 70, 220), 1540, 2, "psi"),
        ("ballooning_dp3000", "Ballooning @ ΔP_int=3000 psi (7\" pipe)", lambda: abs(ballooning_axial_klbf(7, id_7_29, 3000, 0, 0, 0, 0.3, 1000)), 77, 8, "klbf"),
        ("piston_force_packer", "Piston force @ ΔP_int=500 psi (9.625\" pipe)", lambda: abs(piston_force_klbf(9.625, id_9_625, 3500, 3000, 3000, 3000, id_9_625)), 28.5, 10, "klbf"),
        ("thermal_circ_temp", "Circulation temp @ 8,000 ft (relax 5000)", thermal_circ_8k, 167, 5, "°F"),
        ("iso_burst_higher", "ISO 10400 burst > API (7\" 29# N80)", lambda: barlow_burst(7, id_7_29, 80000, "iso") - barlow_burst(7, id_7_29, 80000, "api"), 1176, 5, "psi"),
        ("sour_derate_half_psi", "Sour derating @ 0.5 psi H₂S", lambda: sour_derating_factor(0.5), 0.85, 2, "ratio"),
        ("surge_margin_ppg", "Surge margin (90 ft/min, 25 cP)", lambda: surge_swab_margin_ppg({"pipeSpeedFtMin": 90, "mudPlasticVisc": 25}, True), 0.158, 15, "ppg"),
        ("cement_schedule_5k", "Cement schedule @ 5,000 ft (15.2 ppg)", cement_5k, 3952, 5, "psi"),
        ("wear_depth_12pct", "Wear profile returns 12% @ 7,000 ft", wear_depth_12, 12, 1, "%"),
        ("prob_pp_mult", "Probabilistic P90 PP multiplier (5%)", lambda: probabilistic_factors({"probDesignEnabled": True, "ppUncertaintyPct": 5})[0], 1.05, 0.5, "ratio"),
        ("vme_curve_interpolate", "Manufacturer VME burst @ 200 klbf", lambda: interpolate_burst_at_axial([{"axial_klbf": 0, "burst_psi": 10000}, {"axial_klbf": 200, "burst_psi": 8500}, {"axial_klbf": 400, "burst_psi": 6000}], 200), 8500, 1, "psi"),
        ("mc_percentile_median", "Monte Carlo percentile P50", mc_p50, 0.55, 5, "util"),
    ]


def run_engine_benchmarks() -> dict[str, Any]:
    results = [_run_case(c) for c in benchmark_cases()]
    passed = sum(1 for r in results if r["pass"])
    return {"benchmarks": results, "pass": passed, "total": len(results)}
