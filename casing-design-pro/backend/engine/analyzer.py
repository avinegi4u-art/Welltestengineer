"""Full-well analysis orchestration."""

from __future__ import annotations

from engine.loads import hydrostatic_psi, internal_pressure, interpolate_profile, wear_at_depth
from engine.ratings import calc_pipe_ratings
from engine.triaxial import triaxial_check


def depth_points(top: float, shoe: float, step: float) -> list[float]:
    step = max(step, 250)
    pts = list(range(int(top), int(shoe), int(step)))
    pts.append(int(shoe))
    return sorted(set(pts))


def run_analysis(payload: dict) -> dict:
    inp = payload.get("inputs", {})
    state = payload.get("state", {})
    strings = state.get("strings", [])
    catalog = {p["id"]: p for p in state.get("catalog", [])}
    profiles = state.get("profiles", [])
    wear_profiles = state.get("wearProfiles", {})
    cement_schedule = state.get("cementingSchedule", [])
    scenarios = payload.get("scenarios") or [
        "production", "cementing", "kick", "pressureTest", "running", "surge", "swab"
    ]
    step = inp.get("analysisStepFt", 1000)
    design_code = inp.get("designCode", "api")
    h2s = inp.get("h2sPartialPsi", 0)
    sf = {
        "burst": inp.get("sfBurst", 1.1),
        "collapse": inp.get("sfCollapse", 1.0),
        "tension": inp.get("sfTension", 1.2),
        "triaxial": inp.get("sfTriaxial", 1.25),
    }

    rows = []
    for s in strings:
        pipe = catalog.get(s.get("pipeId"))
        if not pipe:
            continue
        for tvd in depth_points(s.get("top", 0), s.get("shoe", 10000), step):
            pp = interpolate_profile(profiles, tvd, "pp")
            fg = interpolate_profile(profiles, tvd, "fg")
            mw = s.get("fluidInt") or interpolate_profile(profiles, tvd, "mwInt")
            p_mw = hydrostatic_psi(mw, tvd)
            temp = interpolate_profile(profiles, tvd, "temp")
            wear = wear_at_depth(
                tvd, s["id"], pipe.get("wearPct"), wear_profiles, inp.get("defaultWearPct", 0)
            )
            for sc in scenarios:
                p_int = internal_pressure(tvd, sc, pp, fg, p_mw, inp, cement_schedule)
                p_ext = hydrostatic_psi(pp * (1.05 if inp.get("probDesignEnabled") else 1.0), tvd) * 0.65
                axial = p_mw * 0.001  # simplified screening axial placeholder
                ratings = calc_pipe_ratings(
                    pipe["od"], pipe["wt"], pipe.get("grade", "L80"),
                    temp, inp.get("tempDerating", True), wear, design_code, h2s,
                )
                tri = triaxial_check(axial, p_int, p_ext, ratings, sf)
                rows.append({
                    "string": s.get("label", s["id"]),
                    "scenario": sc,
                    "depth": tvd,
                    "util": tri["util"],
                    "mode": tri["mode"],
                    "wear_pct": wear,
                })

    governing = max(rows, key=lambda r: r["util"], default=None)
    return {
        "rows": rows,
        "check_count": len(rows),
        "max_util": governing["util"] if governing else 0,
        "governing": governing,
        "design_code": design_code,
    }
