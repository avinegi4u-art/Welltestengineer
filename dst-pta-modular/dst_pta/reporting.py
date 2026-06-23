"""Auto-generated engineering reports."""

from __future__ import annotations

from datetime import datetime

from .data_loader import PressureSeries
from .interpretation import BuildupInterpretation


def format_buildup_section(idx: int, result: BuildupInterpretation) -> str:
    h = result.horner
    lines = [
        f"--- Buildup #{idx + 1} ---",
        f"Confidence: {result.overall_confidence}",
        "",
    ]
    if h:
        lines += [
            "HORNER ANALYSIS",
            f"  Permeability k     : {h.permeability_md:.2f} md ({h.confidence} confidence, R²={h.r2:.3f})",
            f"  Skin s             : {h.skin:.2f}",
            f"  Reservoir p*       : {h.p_star_psi:.1f} psi",
            f"  Fit window         : {h.fit_start_hr:.3f} – {h.fit_end_hr:.3f} hr ({h.n_points} points)",
            f"  {h.notes}",
            "",
        ]
    lines.append("FLOW REGIMES")
    if result.regimes:
        for r in result.regimes:
            lines.append(f"  • {r.name} ({r.confidence}): {r.hint}")
    else:
        lines.append("  • No confident regime labels — check data quality or Bourdet L.")
    lines.append("")
    if result.typecurve_k_md:
        lines += [
            "TYPE CURVE (radial auto-fit)",
            f"  k = {result.typecurve_k_md:.2f} md, skin = {result.typecurve_skin:.1f}",
            "",
        ]
    if result.wellbore_storage_coeff:
        lines.append(f"Wellbore storage C ≈ {result.wellbore_storage_coeff:.4f} stb/psi (screening)")
    lines.append(result.superposition.notes)
    return "\n".join(lines)


def generate_report(
    series: PressureSeries,
    results: list[BuildupInterpretation],
    qc: dict | None = None,
) -> str:
    """Plain-text auto-report for field / office use."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "DST PRESSURE TRANSIENT ANALYSIS REPORT",
        "=" * 50,
        f"Generated : {now}",
        f"Source    : {series.source}",
        f"Points    : {series.n}",
        "",
    ]
    if qc:
        lines += [
            "DATA QUALITY",
            f"  Outliers removed : {qc.get('outliers_removed', 0)}",
            f"  Points used      : {qc.get('points_out', series.n)}",
            "",
        ]
    if series.cycles:
        lines.append("DST CYCLES")
        for c in series.cycles:
            lines.append(f"  #{c.cycle_id} {c.kind}: {c.start_hr:.2f}–{c.end_hr:.2f} hr, avg rate {c.avg_rate_bpd:.1f} bpd")
        lines.append("")

    if not results:
        lines.append("No interpretable shut-in buildups detected.")
    else:
        for i, r in enumerate(results):
            lines.append(format_buildup_section(i, r))
            lines.append("")

    lines += [
        "INTERPRETATION NOTES",
        "• Superposition uses Agarwal equivalent time and Horner (tp+Δt)/Δt ratio.",
        "• Bourdet derivative with adjustable L — verify radial plateau before finalizing k.",
        "• Screening-grade tool — confirm with service company model for commercial decisions.",
    ]
    return "\n".join(lines)
