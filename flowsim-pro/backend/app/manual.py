"""Generate FlowSim Pro User Manual PDF."""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _styles():
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ManualTitle",
            parent=styles["Heading1"],
            fontSize=22,
            spaceAfter=6,
            textColor=colors.HexColor("#1e3a5f"),
        ),
        "subtitle": ParagraphStyle(
            "ManualSubtitle",
            parent=styles["Normal"],
            fontSize=11,
            textColor=colors.HexColor("#64748b"),
            spaceAfter=20,
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=styles["Heading1"],
            fontSize=16,
            spaceBefore=18,
            spaceAfter=10,
            textColor=colors.HexColor("#1e3a5f"),
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=styles["Heading2"],
            fontSize=13,
            spaceBefore=14,
            spaceAfter=8,
            textColor=colors.HexColor("#2563eb"),
        ),
        "body": ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            spaceAfter=8,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=styles["Normal"],
            fontSize=10,
            leading=13,
            leftIndent=12,
            spaceAfter=4,
        ),
        "code": ParagraphStyle(
            "Code",
            parent=styles["Code"],
            fontSize=9,
            leading=12,
            backColor=colors.HexColor("#f1f5f9"),
            leftIndent=10,
            spaceAfter=8,
        ),
    }


def _bullet_list(items: list[str], style) -> ListFlowable:
    return ListFlowable(
        [ListItem(Paragraph(item, style["bullet"]), leftIndent=12) for item in items],
        bulletType="bullet",
        start="•",
    )


def _table(data: list[list[str]], col_widths=None) -> Table:
    t = Table(data, colWidths=col_widths or [2.5 * inch, 3.8 * inch])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return t


def build_manual_elements(style: dict) -> list:
    el = []

    # Cover
    el.append(Paragraph("FlowSim Pro", style["title"]))
    el.append(Paragraph("User Manual — Steady-State Multiphase Flow Simulator", style["subtitle"]))
    el.append(Paragraph(f"Version 1.0 | {datetime.now().strftime('%B %Y')}", style["body"]))
    el.append(Spacer(1, 0.3 * inch))
    el.append(
        Paragraph(
            "FlowSim Pro is an engineering application for steady-state multiphase flow "
            "in wells, tubing, flowlines, pipelines, and simple production networks. "
            "This manual describes how to start, navigate, and use the application in Cursor Cloud or on a local machine.",
            style["body"],
        )
    )
    el.append(PageBreak())

    # Table of contents
    el.append(Paragraph("Table of Contents", style["h1"]))
    toc = [
        "1. Getting Started",
        "2. Application Layout",
        "3. Dashboard",
        "4. Case Editor",
        "5. Input Tabs Reference",
        "6. Running a Simulation",
        "7. Understanding Results",
        "8. Nodal Analysis",
        "9. Case Comparison & Sensitivity",
        "10. Exporting Reports",
        "11. Model Assumptions",
        "12. Troubleshooting",
        "13. API Reference (Optional)",
    ]
    el.append(_bullet_list(toc, style))
    el.append(PageBreak())

    # 1. Getting Started
    el.append(Paragraph("1. Getting Started", style["h1"]))
    el.append(Paragraph("1.1 Cursor Cloud (Recommended)", style["h2"]))
    el.append(
        Paragraph(
            "When using FlowSim Pro inside a Cursor Cloud workspace, the project files are "
            "already available. You do not need to download anything to your local PC.",
            style["body"],
        )
    )
    el.append(Paragraph("Start the application with two terminals:", style["body"]))
    el.append(
        Paragraph(
            "<b>Terminal 1 — Backend (API &amp; simulation engine):</b><br/>"
            "cd flowsim-pro/backend<br/>"
            "pip install -r requirements.txt<br/>"
            "PYTHONPATH=. python3 -m uvicorn app.main:app --reload --port 8000",
            style["code"],
        )
    )
    el.append(
        Paragraph(
            "<b>Terminal 2 — Frontend (web interface):</b><br/>"
            "cd flowsim-pro/frontend<br/>"
            "npm install<br/>"
            "npm run dev",
            style["code"],
        )
    )
    el.append(
        Paragraph(
            "Open the app in your browser via Cursor port forwarding: <b>http://localhost:3000</b>",
            style["body"],
        )
    )
    el.append(Paragraph("1.2 Local PC", style["h2"]))
    el.append(
        Paragraph(
            "To run on your own computer, clone the repository from GitHub and follow the same "
            "terminal commands above. Requirements: Python 3.10+, Node.js 18+.",
            style["body"],
        )
    )
    el.append(PageBreak())

    # 2. Layout
    el.append(Paragraph("2. Application Layout", style["h1"]))
    el.append(
        Paragraph(
            "The top navigation bar provides access to three main pages and a theme toggle:",
            style["body"],
        )
    )
    el.append(
        _table(
            [
                ["Page", "Purpose"],
                ["Dashboard", "Overview of all cases, quick solve, multi-case selection"],
                ["Case Editor", "Main workspace for editing inputs and viewing live results"],
                ["Results", "Full-size charts and case comparison viewer"],
            ]
        )
    )
    el.append(Spacer(1, 0.15 * inch))
    el.append(Paragraph("Case Editor — Three-Panel Layout", style["h2"]))
    el.append(
        _table(
            [
                ["Panel", "Location", "Function"],
                ["Case Tree", "Left", "Create, select, duplicate, delete, and solve cases"],
                ["Input Forms", "Center-left", "Edit fluid, well, flowline, boundary, nodal, heat inputs"],
                ["Charts & Assumptions", "Center", "Pressure/temperature profiles, nodal curves, model info"],
                ["Results & Diagnostics", "Right", "Summary numbers, warnings, solver messages"],
            ],
            [1.2 * inch, 1.0 * inch, 4.1 * inch],
        )
    )
    el.append(PageBreak())

    # 3. Dashboard
    el.append(Paragraph("3. Dashboard", style["h1"]))
    el.append(
        _bullet_list(
            [
                "View all saved simulation cases in a table.",
                "See summary metrics: liquid rate, bottomhole pressure (BHP).",
                "Click a case name to open it in the Case Editor.",
                "Click the Play (▶) icon to run a simulation without opening the editor.",
                "Click <b>+ New Case</b> to create a blank case.",
                "Check boxes on two or more cases, then click <b>Compare</b> to open the Results viewer.",
            ],
            style,
        )
    )
    el.append(
        Paragraph(
            "On first startup, a sample case <b>Deviated Well - Alpha-1</b> is automatically loaded.",
            style["body"],
        )
    )

    # 4. Case Editor
    el.append(Paragraph("4. Case Editor", style["h1"]))
    el.append(Paragraph("Top Toolbar", style["h2"]))
    el.append(
        _bullet_list(
            [
                "<b>Case name</b> — editable text field; rename your case here.",
                "<b>Save</b> — saves current inputs to the database.",
                "<b>Solve</b> — runs the simulation and updates charts and results.",
                "<b>PDF / JSON / CSV</b> — export the case report in the selected format.",
            ],
            style,
        )
    )
    el.append(Paragraph("Case Tree (Left Panel)", style["h2"]))
    el.append(
        _bullet_list(
            [
                "<b>+ New</b> — creates a new case with default inputs.",
                "Click a case to load it.",
                "Hover over a case for actions: Solve, Duplicate, Delete.",
            ],
            style,
        )
    )
    el.append(PageBreak())

    # 5. Input Tabs
    el.append(Paragraph("5. Input Tabs Reference", style["h1"]))

    el.append(Paragraph("Fluid Tab", style["h2"]))
    el.append(
        _table(
            [
                ["Parameter", "Description / Units"],
                ["Oil API", "Oil API gravity (°API)"],
                ["Gas Gravity", "Gas specific gravity (air = 1)"],
                ["GOR", "Gas-oil ratio (scf/stb)"],
                ["Water Cut", "Fraction of water in total liquid (0–1)"],
                ["Bubble Point", "Bubble-point pressure (psi)"],
                ["Reservoir Temp", "Reservoir temperature (°F)"],
                ["Water Salinity", "Formation water salinity (ppm)"],
            ]
        )
    )
    el.append(Spacer(1, 0.15 * inch))

    el.append(Paragraph("Well Tab", style["h2"]))
    el.append(
        _table(
            [
                ["Parameter", "Description / Units"],
                ["Packer Depth", "Packer setting depth MD (ft)"],
                ["Perforation Depth", "Perforation depth MD (ft)"],
                ["Choke (64ths in)", "Surface choke size in 64ths of an inch"],
                ["Tubing Segments", "MD/TVD top and bottom, inner diameter (in), inclination (°)"],
            ]
        )
    )
    el.append(Spacer(1, 0.15 * inch))

    el.append(Paragraph("Flowline Tab", style["h2"]))
    el.append(
        _table(
            [
                ["Parameter", "Description / Units"],
                ["Length", "Segment length (ft)"],
                ["ID", "Inner diameter (in)"],
                ["Elev Δ", "Elevation change, positive = uphill (ft)"],
                ["Ambient Temp", "Surrounding temperature (°F)"],
            ]
        )
    )
    el.append(Spacer(1, 0.15 * inch))

    el.append(Paragraph("Boundary, Nodal & Heat Transfer Tabs", style["h2"]))
    el.append(
        _table(
            [
                ["Tab", "Key Parameters"],
                ["Boundary", "Liquid rate (stb/d), WHP (psi), optional BHP (psi)"],
                ["Nodal", "Reservoir pressure (psi), PI (stb/d/psi), IPR model (PI or Vogel)"],
                ["Heat Transfer", "Ambient temp (°F), U-value (Btu/hr·ft²·°F), burial, insulation"],
            ]
        )
    )
    el.append(PageBreak())

    # 6. Running simulation
    el.append(Paragraph("6. Running a Simulation", style["h1"]))
    el.append(Paragraph("Recommended workflow:", style["body"]))
    el.append(
        _bullet_list(
            [
                "Select or create a case in the Case Tree.",
                "Enter fluid properties on the Fluid tab.",
                "Define tubing segments on the Well tab (use + Add for multiple segments).",
                "Add flowline segments if modeling surface lines.",
                "Set boundary conditions: rate and wellhead pressure.",
                "Configure nodal analysis parameters if studying inflow/outflow balance.",
                "Click <b>Save</b>, then click <b>Solve</b>.",
                "Review charts in the center panel and summary values on the right.",
            ],
            style,
        )
    )
    el.append(
        Paragraph(
            "<b>Boundary condition modes:</b> If BHP is left blank, the solver marches top-down "
            "from WHP to calculate BHP (VLP mode). If BHP is specified, the solver marches "
            "bottom-up from BHP to calculate WHP.",
            style["body"],
        )
    )

    # 7. Results
    el.append(Paragraph("7. Understanding Results", style["h1"]))
    el.append(Paragraph("Results Panel (Right)", style["h2"]))
    el.append(
        _table(
            [
                ["Output", "Meaning"],
                ["Liquid Rate", "Total liquid production rate (stb/d)"],
                ["WHP", "Wellhead pressure (psi)"],
                ["BHP", "Bottomhole pressure at perforations (psi)"],
                ["Flowline ΔP", "Pressure drop across flowline segments (psi)"],
                ["Nodal Rate", "Operating rate from IPR/VLP intersection (stb/d)"],
            ]
        )
    )
    el.append(Spacer(1, 0.15 * inch))
    el.append(Paragraph("Charts (Center)", style["h2"]))
    el.append(
        _bullet_list(
            [
                "<b>Well Pressure & Temperature vs MD</b> — blue = pressure, red = temperature along measured depth.",
                "<b>Flowline Pressure Profile</b> — pressure vs distance along the pipeline.",
                "<b>Nodal Analysis (IPR/VLP)</b> — blue = inflow (IPR), orange = outflow (VLP), red dot = operating point.",
            ],
            style,
        )
    )
    el.append(PageBreak())

    # 8. Nodal
    el.append(Paragraph("8. Nodal Analysis", style["h1"]))
    el.append(
        Paragraph(
            "Nodal analysis finds the operating point where the Inflow Performance Relationship (IPR) "
            "intersects the Vertical Lift Performance (VLP) curve.",
            style["body"],
        )
    )
    el.append(Paragraph("IPR Models", style["h2"]))
    el.append(
        _bullet_list(
            [
                "<b>Linear PI</b> — BHP = Pr − Q/PI. Simple, good for undersaturated or moderate drawdown.",
                "<b>Vogel</b> — Non-linear IPR for solution-gas drive reservoirs below bubble point.",
            ],
            style,
        )
    )
    el.append(
        Paragraph(
            "The operating point rate and BHP are shown in the Results panel and marked on the nodal chart. "
            "Convergence error indicates how closely IPR and VLP pressures match at the solution rate.",
            style["body"],
        )
    )

    # 9. Comparison
    el.append(Paragraph("9. Case Comparison & Sensitivity", style["h1"]))
    el.append(
        _bullet_list(
            [
                "On the Dashboard, select 2+ cases with checkboxes and click Compare.",
                "The Results page shows a bar chart and table comparing rate, WHP, BHP, and flowline ΔP.",
                "Sensitivity analysis is available via the API (/api/sensitivity) for choke, WHP, tubing ID, GOR, and water cut.",
            ],
            style,
        )
    )

    # 10. Export
    el.append(Paragraph("10. Exporting Reports", style["h1"]))
    el.append(
        _table(
            [
                ["Format", "Contents"],
                ["PDF", "Engineering report with assumptions, summary table, fluid properties, warnings"],
                ["JSON", "Full case inputs and outputs for archiving or external tools"],
                ["CSV", "Well pressure/temperature profile (MD, P, T, holdup)"],
            ]
        )
    )
    el.append(PageBreak())

    # 11. Assumptions
    el.append(Paragraph("11. Model Assumptions", style["h1"]))
    el.append(
        Paragraph(
            "The Assumptions panel in the Case Editor lists the correlations in use. Key assumptions:",
            style["body"],
        )
    )
    el.append(
        _bullet_list(
            [
                "<b>Fluid:</b> Black-oil model with Standing Bo and Beggs-Robinson oil viscosity.",
                "<b>Multiphase flow:</b> Simplified drift-flux liquid holdup with Darcy-Weisbach friction.",
                "<b>Heat transfer:</b> Steady-state exponential approach to ambient (lumped UA).",
                "<b>IPR:</b> Linear productivity index or Vogel correlation.",
                "<b>Network:</b> Iterative Gauss-Seidel pressure balance for tree topology.",
                "<b>Units:</b> Field units throughout — psi, ft, stb/d, °F.",
            ],
            style,
        )
    )
    el.append(
        Paragraph(
            "These are simplified engineering correlations suitable for screening studies. "
            "Results should be validated against field data or higher-fidelity simulators for critical decisions.",
            style["body"],
        )
    )

    # 12. Troubleshooting
    el.append(Paragraph("12. Troubleshooting", style["h1"]))
    el.append(
        _table(
            [
                ["Problem", "Solution"],
                ["Blank page / cannot connect", "Ensure both backend (port 8000) and frontend (port 3000) are running"],
                ["API error when solving", "Restart backend; check Terminal 1 for Python errors"],
                ["No cases listed", "Restart backend to trigger sample case seeding"],
                ["Charts empty after Solve", "Check Results panel for warnings; verify inputs are realistic"],
                ["BHP less than WHP", "Check rate, tubing size, and deviation survey; reduce rate or increase tubing ID"],
                ["Dark/light theme", "Click moon/sun icon in top-right corner"],
            ],
            [2.0 * inch, 4.3 * inch],
        )
    )

    # 13. API
    el.append(Paragraph("13. API Reference (Optional)", style["h1"]))
    el.append(
        Paragraph(
            "Interactive API documentation is available at <b>http://localhost:8000/docs</b> when the backend is running.",
            style["body"],
        )
    )
    el.append(
        _table(
            [
                ["Endpoint", "Method", "Description"],
                ["/api/health", "GET", "Health check"],
                ["/api/cases", "GET/POST", "List or create cases"],
                ["/api/cases/{id}", "GET/PUT/DELETE", "Read, update, or delete a case"],
                ["/api/solve", "POST", "Run simulation"],
                ["/api/compare", "POST", "Compare multiple cases"],
                ["/api/sensitivity", "POST", "Sensitivity analysis"],
                ["/api/export", "POST", "Export PDF, JSON, or CSV"],
            ],
            [1.8 * inch, 0.8 * inch, 3.7 * inch],
        )
    )
    el.append(Spacer(1, 0.3 * inch))
    el.append(
        Paragraph(
            "— End of FlowSim Pro User Manual —",
            ParagraphStyle("End", parent=style["body"], alignment=1, textColor=colors.HexColor("#94a3b8")),
        )
    )

    return el


def generate_user_manual_pdf(output_path: str | Path | None = None) -> bytes:
    """Build and optionally save the user manual PDF. Returns PDF bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.85 * inch,
        rightMargin=0.85 * inch,
        title="FlowSim Pro User Manual",
        author="FlowSim Pro",
    )
    style = _styles()
    doc.build(build_manual_elements(style))
    pdf_bytes = buffer.getvalue()

    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(pdf_bytes)

    return pdf_bytes


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent.parent / "docs" / "FlowSim_Pro_User_Manual.pdf"
    generate_user_manual_pdf(out)
    print(f"Manual written to: {out}")
