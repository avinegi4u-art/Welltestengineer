"""Full-well analysis orchestration."""

from __future__ import annotations

from typing import Any

from engine.loads import (
    axial_force_at_depth,
    external_pressure_at_depth,
    external_zone,
    internal_pressure_at_depth,
    interpolate_profile,
    scenarios_for_load_generation,
    temperature_at_depth,
    wear_at_depth,
)
from engine.ratings import calc_pipe_ratings
from engine.triaxial import triaxial_check

SCENARIO_LABELS: dict[str, str] = {
    "production": "Production / Worst Case",
    "cementing": "Cementing / Displacement",
    "pressureTest": "Pressure Test",
    "kick": "Kick / Well Control",
    "evacuation": "Evacuation / Lost Returns",
    "stimulation": "Stimulation / Frac",
    "running": "Running In / Overpull",
    "surge": "Surge (Running)",
    "swab": "Swab (Tripping Out)",
    "packerSet": "Packer Set / Test",
    "annulusIntegrity": "Sealed Annulus / APB",
    "thermalCirculation": "Thermal — Circulation",
    "thermalShutin": "Thermal — Shut-in",
    "thermalProduction": "Thermal — Hot Production",
    "thermalInjection": "Thermal — Cold Injection",
    "tubingMovement": "Tubing / Packer Movement",
}


def depth_points(top: float, shoe: float, step: float) -> list[float]:
    step = max(step, 250)
    pts = list(range(int(top), int(shoe), int(step)))
    pts.append(int(shoe))
    return sorted(set(pts))


def _row_required_available(tri: dict, mode: str) -> tuple[float, float, str]:
    if mode == "Collapse":
        return tri["collapse_req"], tri["collapse_avail"], "psi"
    if mode == "Tension":
        return tri["tension_req"] / 1000, tri["tension_avail"] / 1000, "klbf"
    if mode == "Compression":
        return tri["comp_req"] / 1000, tri["comp_avail"] / 1000, "klbf"
    if mode == "Triaxial":
        return tri["tri_req"], tri["tri_avail"], "lbf"
    return tri["burst_req"], tri["burst_avail"], "psi"


def run_analysis(payload: dict) -> dict:
    inp = payload.get("inputs", {})
    state = payload.get("state", {})
    strings = state.get("strings", [])
    catalog = {p["id"]: p for p in state.get("catalog", [])}
    profiles = state.get("profiles", [])
    wear_profiles = state.get("wearProfiles", {})
    cement_schedule = state.get("cementingSchedule", [])
    scenarios = payload.get("scenarios") or scenarios_for_load_generation(inp, state)
    step = inp.get("analysisStepFt", 1000)
    design_code = inp.get("designCode", "api")
    h2s = inp.get("h2sPartialPsi", 0)
    sf = {
        "burst": inp.get("sfBurst", 1.1),
        "collapse": inp.get("sfCollapse", 1.0),
        "tension": inp.get("sfTension", 1.2),
        "triaxial": inp.get("sfTriaxial", 1.25),
    }

    rows: list[dict[str, Any]] = []
    loads: list[dict[str, Any]] = []

    for s in strings:
        pipe = catalog.get(s.get("pipeId"))
        if not pipe:
            continue
        for tvd in depth_points(s.get("top", 0), s.get("shoe", 10000), step):
            temp = temperature_at_depth(tvd, inp, state, None, profiles)
            wear = wear_at_depth(
                tvd, s["id"], pipe.get("wearPct"), wear_profiles, inp.get("defaultWearPct", 0)
            )
            zone = external_zone(tvd, s)
            for sc in scenarios:
                p_int = internal_pressure_at_depth(tvd, s, sc, inp, profiles, state, cement_schedule)
                p_ext = external_pressure_at_depth(tvd, s, sc, inp, profiles, state)
                axial = axial_force_at_depth(tvd, s, inp, state, profiles, cement_schedule, sc, catalog)
                ratings = calc_pipe_ratings(
                    pipe["od"], pipe["wt"], pipe.get("grade", "L80"),
                    temp, inp.get("tempDerating", True), wear, design_code, h2s,
                )
                tri = triaxial_check(axial, p_int, p_ext, ratings, sf)
                diff_p = p_int - p_ext
                required, available, unit = _row_required_available(tri, tri["mode"])
                label = s.get("label", s["id"])
                scenario_label = SCENARIO_LABELS.get(sc, sc)
                load_name = f"{label} — {scenario_label} @ {tvd} ft"

                load_row = {
                    "id": f"lc_{s['id']}_{sc}_{tvd}",
                    "name": f"{label} — {scenario_label}",
                    "stringId": s["id"],
                    "depth": tvd,
                    "pInt": p_int,
                    "pExt": p_ext,
                    "axial": axial,
                    "temp": temp,
                    "scenario": sc,
                    "zone": zone,
                }
                loads.append(load_row)

                rows.append({
                    "string": label,
                    "string_id": s["id"],
                    "load_name": load_name,
                    "mode": tri["mode"],
                    "required": required,
                    "available": available,
                    "util": tri["util"],
                    "unit": unit,
                    "depth": tvd,
                    "zone": zone,
                    "scenario": sc,
                    "burst_util": tri["burst_util"],
                    "collapse_util": tri["collapse_util"],
                    "axial_util": tri["axial_util"],
                    "tri_util": tri["tri_util"],
                    "burst_load": max(diff_p, 0),
                    "collapse_load": max(-diff_p, 0),
                    "burst_rating": tri["burst_avail"],
                    "collapse_rating": tri["collapse_avail"],
                    "axial_load": abs(axial),
                    "axial_rating": ratings["tension"],
                    "p_int": p_int,
                    "p_ext": p_ext,
                    "axial_klbf": axial,
                    "wear_pct": wear,
                    "temp_f": temp,
                    "engine": "python",
                })

    governing = max(rows, key=lambda r: r["util"], default=None)
    governing_summary = None
    if governing:
        governing_summary = {
            "string": governing["string"],
            "load_name": governing["load_name"],
            "mode": governing["mode"],
            "util": governing["util"],
            "depth": governing["depth"],
            "detail": (
                f"{governing['string']} · wear {governing['wear_pct']:.0f}% · "
                f"{governing['scenario']} · {governing['zone']}"
            ),
        }

    return {
        "rows": rows,
        "loads": loads,
        "check_count": len(rows),
        "max_util": governing["util"] if governing else 0,
        "governing": governing_summary,
        "design_code": design_code,
        "engine": "python",
    }
