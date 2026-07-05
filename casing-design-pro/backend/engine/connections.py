"""Connection VME limits — generic API efficiencies and manufacturer CSV curves."""

from __future__ import annotations

import math
from typing import Any

from engine.triaxial import biaxial_burst_factor, biaxial_collapse_factor
from engine.vme import curve_envelope, interpolate_burst_at_axial, interpolate_tension_at_pressure

CONNECTION_VME: dict[str, dict[str, Any]] = {
    "BTC": {"burst_eff": 1.0, "collapse_eff": 1.0, "tension_eff": 0.55, "compression_eff": 0.55, "label": "API BTC"},
    "LTC": {"burst_eff": 0.95, "collapse_eff": 0.95, "tension_eff": 0.55, "compression_eff": 0.55, "label": "API LTC"},
    "STC": {"burst_eff": 0.9, "collapse_eff": 0.9, "tension_eff": 0.5, "compression_eff": 0.5, "label": "API STC"},
    "VAM TOP": {"burst_eff": 0.92, "collapse_eff": 0.88, "tension_eff": 0.72, "compression_eff": 0.65, "label": "VAM TOP"},
    "VAM 21": {"burst_eff": 0.9, "collapse_eff": 0.86, "tension_eff": 0.7, "compression_eff": 0.63, "label": "VAM 21"},
    "TSH": {"burst_eff": 0.88, "collapse_eff": 0.85, "tension_eff": 0.68, "compression_eff": 0.6, "label": "Tenaris TSH"},
    "FOX": {"burst_eff": 0.9, "collapse_eff": 0.87, "tension_eff": 0.7, "compression_eff": 0.62, "label": "Fox Premium"},
}


def iso_ellipse_burst_allowance(pb0: float, ft0_klbf: float, axial_klbf: float) -> float:
    if pb0 <= 0 or ft0_klbf <= 0:
        return 0.0
    if axial_klbf <= 0:
        return pb0
    r = min(axial_klbf / ft0_klbf, 1.0)
    return pb0 * math.sqrt(max(0.0, 1.0 - r * r))


def iso_ellipse_tension_allowance(ft0_klbf: float, pb0_psi: float, diff_p: float) -> float:
    if ft0_klbf <= 0 or pb0_psi <= 0:
        return 0.0
    p = max(diff_p, 0.0)
    if p <= 0:
        return ft0_klbf
    r = min(p / pb0_psi, 1.0)
    return ft0_klbf * math.sqrt(max(0.0, 1.0 - r * r))


def _normalize_vme_points(points: list[dict]) -> list[dict]:
    return [
        {"axial_klbf": p.get("axial_klbf", p.get("axialKlbf", 0)), "burst_psi": p.get("burst_psi", p.get("burstPsi", 0))}
        for p in points
    ]


def get_vme_curve_for_pipe(pipe: dict | None, vme_curves: dict[str, Any]) -> dict | None:
    if not pipe:
        return None
    curve_id = pipe.get("vmeCurveId")
    if curve_id and vme_curves.get(curve_id):
        return vme_curves[curve_id]
    key = f"{pipe.get('conn')}_{pipe.get('od')}_{pipe.get('wt')}_{pipe.get('grade')}".replace(" ", "_")
    if vme_curves.get(key):
        return vme_curves[key]
    return vme_curves.get(pipe.get("conn"))


def connection_vme_limits(
    pipe_ratings: dict,
    conn_name: str,
    axial_klbf: float = 0,
    diff_p: float = 0,
    pipe: dict | None = None,
    vme_curves: dict[str, Any] | None = None,
) -> dict[str, Any]:
    vme_curves = vme_curves or {}
    curve = get_vme_curve_for_pipe(pipe, vme_curves) if pipe else vme_curves.get(conn_name)

    if curve and curve.get("points"):
        points = _normalize_vme_points(curve["points"])
        env = curve_envelope(points)
        conn_burst0 = curve.get("conn_burst0") or curve.get("connBurst0") or env["conn_burst0"]
        conn_tension0 = curve.get("conn_tension0") or curve.get("connTension0") or env["conn_tension0"]
        burst_body = pipe_ratings["burst"] * biaxial_burst_factor(
            axial_klbf, pipe_ratings["yield_psi"], pipe_ratings["od"], pipe_ratings["id"]
        )
        collapse_body = pipe_ratings["collapse"] * biaxial_collapse_factor(
            axial_klbf, pipe_ratings["yield_psi"], pipe_ratings["od"], pipe_ratings["id"]
        )
        burst_vme = interpolate_burst_at_axial(points, max(axial_klbf, 0))
        tension_vme = iso_ellipse_tension_allowance(conn_tension0, conn_burst0, diff_p)
        return {
            "burst": min(burst_body, burst_vme),
            "collapse": collapse_body,
            "tension": min(pipe_ratings["tension"], tension_vme),
            "compression": min(pipe_ratings.get("compression", pipe_ratings["tension"]), conn_tension0 * 0.55),
            "vme": {
                "label": curve.get("label") or curve.get("manufacturer") or "Manufacturer VME",
                "source": "manufacturer_csv",
                "conn_burst0": conn_burst0,
                "conn_tension0": conn_tension0,
                "burst_vme": burst_vme,
                "tension_vme": tension_vme,
                "point_count": len(points),
            },
        }

    vme = CONNECTION_VME.get(conn_name, CONNECTION_VME["BTC"])
    conn_burst0 = pipe_ratings["burst"] * vme["burst_eff"]
    conn_collapse0 = pipe_ratings["collapse"] * vme["collapse_eff"]
    conn_tension0 = pipe_ratings["tension"] * vme["tension_eff"]
    conn_comp0 = pipe_ratings.get("compression", pipe_ratings["tension"]) * vme["compression_eff"]

    burst_body = pipe_ratings["burst"] * biaxial_burst_factor(
        axial_klbf, pipe_ratings["yield_psi"], pipe_ratings["od"], pipe_ratings["id"]
    )
    collapse_body = pipe_ratings["collapse"] * biaxial_collapse_factor(
        axial_klbf, pipe_ratings["yield_psi"], pipe_ratings["od"], pipe_ratings["id"]
    )
    burst_vme = iso_ellipse_burst_allowance(conn_burst0, conn_tension0, max(axial_klbf, 0))
    collapse_vme = collapse_body * vme["collapse_eff"]
    tension_vme = iso_ellipse_tension_allowance(conn_tension0, conn_burst0, diff_p)

    return {
        "burst": min(burst_body, burst_vme),
        "collapse": min(collapse_body, collapse_vme),
        "tension": min(pipe_ratings["tension"], tension_vme),
        "compression": min(pipe_ratings.get("compression", pipe_ratings["tension"]), conn_comp0),
        "vme": {
            "label": vme["label"],
            "conn_burst0": conn_burst0,
            "conn_collapse0": conn_collapse0,
            "conn_tension0": conn_tension0,
            "conn_comp0": conn_comp0,
            "burst_vme": burst_vme,
            "collapse_vme": collapse_vme,
            "tension_vme": tension_vme,
        },
    }


def connection_limits(
    pipe_ratings: dict,
    conn_name: str,
    axial_klbf: float = 0,
    diff_p: float = 0,
    pipe: dict | None = None,
    vme_curves: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return connection_vme_limits(pipe_ratings, conn_name, axial_klbf, diff_p, pipe, vme_curves)
