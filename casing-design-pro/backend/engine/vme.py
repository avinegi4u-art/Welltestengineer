"""Manufacturer connection VME curves — burst vs axial interpolation."""

from __future__ import annotations

import math
from typing import Any


def normalize_curve_points(points: list[dict[str, float]]) -> list[dict[str, float]]:
    """Sort by axial and dedupe."""
    sorted_pts = sorted(points, key=lambda p: p.get("axial_klbf", p.get("axial", 0)))
    out: list[dict[str, float]] = []
    for p in sorted_pts:
        axial = float(p.get("axial_klbf", p.get("axial", 0)))
        burst = float(p.get("burst_psi", p.get("burst", 0)))
        if out and abs(out[-1]["axial_klbf"] - axial) < 1e-6:
            out[-1] = {"axial_klbf": axial, "burst_psi": burst}
        else:
            out.append({"axial_klbf": axial, "burst_psi": burst})
    return out


def curve_envelope(points: list[dict[str, float]]) -> dict[str, float]:
    pts = normalize_curve_points(points)
    if not pts:
        return {"conn_burst0": 0, "conn_tension0": 0}
    burst0 = max(pts[0]["burst_psi"], max(p["burst_psi"] for p in pts if p["axial_klbf"] <= 0.01))
    tension0 = max(p["axial_klbf"] for p in pts)
    return {"conn_burst0": burst0, "conn_tension0": tension0}


def interpolate_burst_at_axial(points: list[dict[str, float]], axial_klbf: float) -> float:
    pts = normalize_curve_points(points)
    if not pts:
        return 0.0
    if axial_klbf <= pts[0]["axial_klbf"]:
        return pts[0]["burst_psi"]
    if axial_klbf >= pts[-1]["axial_klbf"]:
        return max(pts[-1]["burst_psi"], 0)
    for i in range(1, len(pts)):
        if axial_klbf <= pts[i]["axial_klbf"]:
            a0, b0 = pts[i - 1]["axial_klbf"], pts[i - 1]["burst_psi"]
            a1, b1 = pts[i]["axial_klbf"], pts[i]["burst_psi"]
            f = (axial_klbf - a0) / (a1 - a0) if a1 != a0 else 0
            return b0 + f * (b1 - b0)
    return pts[-1]["burst_psi"]


def interpolate_tension_at_pressure(
    points: list[dict[str, float]], conn_burst0: float, conn_tension0: float, diff_p: float,
) -> float:
    """ISO-style inverse: tension allowance from burst-pressure coupling."""
    if conn_burst0 <= 0 or conn_tension0 <= 0:
        return 0.0
    if diff_p <= 0:
        return conn_tension0
    r = min(diff_p / conn_burst0, 1.0)
    return conn_tension0 * math.sqrt(max(0.0, 1.0 - r * r))


def connection_limits_from_curve(
    pipe_ratings: dict[str, Any],
    curve: dict[str, Any],
    axial_klbf: float = 0,
    diff_p: float = 0,
) -> dict[str, Any]:
    points = curve.get("points", [])
    env = curve_envelope(points)
    conn_burst0 = curve.get("conn_burst0") or env["conn_burst0"]
    conn_tension0 = curve.get("conn_tension0") or env["conn_tension0"]
    burst_vme = interpolate_burst_at_axial(points, max(axial_klbf, 0))
    tension_vme = interpolate_tension_at_pressure(points, conn_burst0, conn_tension0, diff_p)
    label = curve.get("label") or curve.get("manufacturer", "Manufacturer VME")
    return {
        "burst": min(pipe_ratings["burst"], burst_vme),
        "collapse": pipe_ratings["collapse"],
        "tension": min(pipe_ratings["tension"], tension_vme),
        "compression": pipe_ratings.get("compression", pipe_ratings["tension"]),
        "vme": {
            "label": label,
            "source": "manufacturer_csv",
            "conn_burst0": conn_burst0,
            "conn_tension0": conn_tension0,
            "burst_vme": burst_vme,
            "tension_vme": tension_vme,
            "point_count": len(points),
        },
    }


def parse_vme_csv_rows(rows: list[list[str]]) -> list[dict[str, Any]]:
    """Parse CSV into one or more VME curves."""
    if not rows:
        return []
    hdr = [c.strip().lower().replace(" ", "_") for c in rows[0]]
    has_header = any(k in hdr for k in ("axial_klbf", "axial", "burst_psi", "burst", "fa", "pb"))
    start = 1 if has_header else 0

    def col(row: list[str], name: str, alt: str = "") -> str:
        for n in (name, alt):
            if n in hdr:
                return row[hdr.index(n)]
        return ""

    curves: dict[str, dict[str, Any]] = {}
    for row in rows[start:]:
        if not row or all(not c.strip() for c in row):
            continue
        curve_id = col(row, "curve_id", "id") or col(row, "connection", "conn") or "imported"
        if curve_id not in curves:
            curves[curve_id] = {
                "id": curve_id.replace(" ", "_"),
                "label": col(row, "label") or curve_id,
                "manufacturer": col(row, "manufacturer", "mfr"),
                "connection": col(row, "connection", "conn"),
                "od": float(col(row, "od") or 0) or None,
                "wt": float(col(row, "ppf", "wt") or 0) or None,
                "grade": col(row, "grade"),
                "points": [],
            }
        axial = float(col(row, "axial_klbf", "axial") or col(row, "fa") or 0)
        burst = float(col(row, "burst_psi", "burst") or col(row, "pb") or 0)
        curves[curve_id]["points"].append({"axial_klbf": axial, "burst_psi": burst})

    result = []
    for c in curves.values():
        c["points"] = normalize_curve_points(c["points"])
        env = curve_envelope(c["points"])
        c["conn_burst0"] = env["conn_burst0"]
        c["conn_tension0"] = env["conn_tension0"]
        result.append(c)
    return result
