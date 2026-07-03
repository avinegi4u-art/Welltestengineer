"""PDF report generation for simulation cases."""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def generate_pdf_report(case_name: str, inputs: dict, outputs: dict) -> bytes:
    """Generate engineering PDF report."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=12,
        textColor=colors.HexColor("#1e3a5f"),
    )
    heading_style = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontSize=13,
        spaceBefore=16,
        spaceAfter=8,
        textColor=colors.HexColor("#2563eb"),
    )
    body = styles["Normal"]

    elements = []
    elements.append(Paragraph("FlowSim Pro — Engineering Report", title_style))
    elements.append(Paragraph(f"Case: {case_name}", body))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}", body))
    elements.append(Spacer(1, 0.25 * inch))

    # Assumptions
    elements.append(Paragraph("Model Assumptions", heading_style))
    assumptions = outputs.get("assumptions", {})
    for key, val in assumptions.items():
        elements.append(Paragraph(f"<b>{key.replace('_', ' ').title()}:</b> {val}", body))

    # Summary
    elements.append(Paragraph("Results Summary", heading_style))
    summary = outputs.get("summary", {})
    summary_data = [["Parameter", "Value"]]
    for k, v in summary.items():
        summary_data.append([k.replace("_", " ").title(), f"{v:.2f}" if isinstance(v, float) else str(v)])
    if len(summary_data) > 1:
        t = Table(summary_data, colWidths=[3 * inch, 2.5 * inch])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4f8")]),
                ]
            )
        )
        elements.append(t)

    # Fluid properties
    elements.append(Paragraph("Fluid Properties", heading_style))
    fluid = outputs.get("fluid_summary", {})
    fluid_data = [["Property", "Value"]]
    for k, v in fluid.items():
        fluid_data.append([k.replace("_", " ").title(), str(v)])
    if len(fluid_data) > 1:
        t2 = Table(fluid_data, colWidths=[3 * inch, 2.5 * inch])
        t2.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 9), ("GRID", (0, 0), (-1, -1), 0.5, colors.grey)]))
        elements.append(t2)

    # Warnings
    warnings = outputs.get("warnings", [])
    if warnings:
        elements.append(Paragraph("Warnings", heading_style))
        for w in warnings:
            elements.append(Paragraph(f"• {w}", body))

    doc.build(elements)
    return buffer.getvalue()
