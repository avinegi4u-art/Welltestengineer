"""FastAPI route handlers."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import SimulationCase, get_db
from app.report import generate_pdf_report
from app.schemas import (
    CaseCreate,
    CaseResponse,
    CaseUpdate,
    CompareRequest,
    ExportRequest,
    SensitivityRequest,
    SolveRequest,
)
from engine.fluid import FluidModel, FluidProperties
from engine.nodal import NodalAnalyzer
from engine.solver import SimulationSolver
from engine.well import TubingSegment, WellGeometry

router = APIRouter()


def _case_to_dict(case: SimulationCase) -> dict:
    return {
        "name": case.name,
        "description": case.description,
        "case_type": case.case_type,
        **case.inputs,
    }


def _output_to_dict(output) -> dict:
    return {
        "success": output.success,
        "warnings": output.warnings,
        "assumptions": output.assumptions,
        "fluid_summary": output.fluid_summary,
        "well_profile": output.well_profile,
        "flowline_profile": output.flowline_profile,
        "nodal_analysis": output.nodal_analysis,
        "network_results": output.network_results,
        "summary": output.summary,
        "diagnostics": output.diagnostics,
    }


@router.get("/health")
def health():
    return {"status": "ok", "app": "FlowSim Pro", "version": "1.0.0"}


@router.get("/manual")
def download_manual():
    """Download the FlowSim Pro user manual PDF."""
    from pathlib import Path

    from fastapi.responses import Response

    manual_path = Path(__file__).parent.parent.parent / "docs" / "FlowSim_Pro_User_Manual.pdf"
    if not manual_path.exists():
        from app.manual import generate_user_manual_pdf

        generate_user_manual_pdf(manual_path)
    return Response(
        content=manual_path.read_bytes(),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="FlowSim_Pro_User_Manual.pdf"'},
    )


@router.post("/cases", response_model=CaseResponse)
def create_case(payload: CaseCreate, db: Session = Depends(get_db)):
    inputs = payload.model_dump()
    name = inputs.pop("name")
    description = inputs.pop("description", "")
    case_type = inputs.pop("case_type", "well_tubing_flowline")

    case = SimulationCase(
        name=name,
        description=description,
        case_type=case_type,
    )
    case.inputs = inputs
    db.add(case)
    db.commit()
    db.refresh(case)
    return CaseResponse(
        id=case.id,
        name=case.name,
        description=case.description,
        case_type=case.case_type,
        inputs=case.inputs,
        outputs=case.outputs,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


@router.get("/cases", response_model=list[CaseResponse])
def list_cases(db: Session = Depends(get_db)):
    cases = db.query(SimulationCase).order_by(SimulationCase.updated_at.desc()).all()
    return [
        CaseResponse(
            id=c.id,
            name=c.name,
            description=c.description,
            case_type=c.case_type,
            inputs=c.inputs,
            outputs=c.outputs,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in cases
    ]


@router.get("/cases/{case_id}", response_model=CaseResponse)
def get_case(case_id: int, db: Session = Depends(get_db)):
    case = db.query(SimulationCase).filter(SimulationCase.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    return CaseResponse(
        id=case.id,
        name=case.name,
        description=case.description,
        case_type=case.case_type,
        inputs=case.inputs,
        outputs=case.outputs,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


@router.put("/cases/{case_id}", response_model=CaseResponse)
def update_case(case_id: int, payload: CaseUpdate, db: Session = Depends(get_db)):
    case = db.query(SimulationCase).filter(SimulationCase.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")

    if payload.name is not None:
        case.name = payload.name
    if payload.description is not None:
        case.description = payload.description
    if payload.case_type is not None:
        case.case_type = payload.case_type

    current = case.inputs
    for field in ("fluid", "well", "flowline", "nodal", "network", "heat_transfer", "boundary_conditions"):
        val = getattr(payload, field, None)
        if val is not None:
            current[field] = val.model_dump() if hasattr(val, "model_dump") else val
    case.inputs = current

    db.commit()
    db.refresh(case)
    return CaseResponse(
        id=case.id,
        name=case.name,
        description=case.description,
        case_type=case.case_type,
        inputs=case.inputs,
        outputs=case.outputs,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


@router.delete("/cases/{case_id}")
def delete_case(case_id: int, db: Session = Depends(get_db)):
    case = db.query(SimulationCase).filter(SimulationCase.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    db.delete(case)
    db.commit()
    return {"deleted": case_id}


@router.post("/cases/{case_id}/duplicate", response_model=CaseResponse)
def duplicate_case(case_id: int, db: Session = Depends(get_db)):
    case = db.query(SimulationCase).filter(SimulationCase.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    new_case = SimulationCase(
        name=f"{case.name} (Copy)",
        description=case.description,
        case_type=case.case_type,
    )
    new_case.inputs = case.inputs
    new_case.outputs = case.outputs
    db.add(new_case)
    db.commit()
    db.refresh(new_case)
    return CaseResponse(
        id=new_case.id,
        name=new_case.name,
        description=new_case.description,
        case_type=new_case.case_type,
        inputs=new_case.inputs,
        outputs=new_case.outputs,
        created_at=new_case.created_at,
        updated_at=new_case.updated_at,
    )


@router.post("/solve")
def solve_case(request: SolveRequest, db: Session = Depends(get_db)):
    if request.case_id:
        case = db.query(SimulationCase).filter(SimulationCase.id == request.case_id).first()
        if not case:
            raise HTTPException(404, "Case not found")
        solver_input = _case_to_dict(case)
    elif request.inputs:
        d = request.inputs.model_dump()
        solver_input = {
            "case_name": d.pop("name"),
            "case_type": d.pop("case_type"),
            **d,
        }
    else:
        raise HTTPException(400, "Provide case_id or inputs")

    solver = SimulationSolver(solver_input)
    output = solver.solve()
    result = _output_to_dict(output)

    if request.case_id:
        case.outputs = result
        db.commit()

    return result


@router.post("/compare")
def compare_cases(request: CompareRequest, db: Session = Depends(get_db)):
    outputs = []
    for cid in request.case_ids:
        case = db.query(SimulationCase).filter(SimulationCase.id == cid).first()
        if case and case.outputs:
            outputs.append(case.outputs)
        elif case:
            solver = SimulationSolver(_case_to_dict(case))
            out = solver.solve()
            outputs.append(_output_to_dict(out))
    return SimulationSolver.compare_cases(outputs)


@router.post("/sensitivity")
def sensitivity_analysis(request: SensitivityRequest, db: Session = Depends(get_db)):
    case = db.query(SimulationCase).filter(SimulationCase.id == request.case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")

    inputs = case.inputs
    fluid = FluidModel(FluidProperties(**inputs.get("fluid", {})))
    well_data = inputs.get("well", {})
    segments = [TubingSegment(**{**s, "tvd_top_ft": s.get("tvd_top_ft", s["md_top_ft"]), "tvd_bottom_ft": s.get("tvd_bottom_ft", s["md_bottom_ft"])}) for s in well_data.get("segments", [])]
    well_geo = WellGeometry(
        segments=segments,
        packer_depth_ft=well_data.get("packer_depth_ft", 8000),
        perforation_depth_ft=well_data.get("perforation_depth_ft", 8500),
        choke_size_64_in=well_data.get("choke_size_64_in", 32),
        wellhead_pressure_psi=inputs.get("boundary_conditions", {}).get("wellhead_pressure_psi", 500),
    )
    nodal_cfg = inputs.get("nodal", {})
    analyzer = NodalAnalyzer(
        fluid,
        well_geo,
        reservoir_pressure_psi=nodal_cfg.get("reservoir_pressure_psi", 3500),
        productivity_index_stb_d_psi=nodal_cfg.get("productivity_index", 2.0),
        ipr_model=nodal_cfg.get("ipr_model", "pi"),
        flow_correlation="beggs_brill",
    )
    result = analyzer.sensitivity(request.parameter, request.values, include_vlp_curves=True)
    return analyzer.sensitivity_to_dict(result)


@router.post("/export")
def export_report(request: ExportRequest, db: Session = Depends(get_db)):
    case = db.query(SimulationCase).filter(SimulationCase.id == request.case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")

    if not case.outputs:
        solver = SimulationSolver(_case_to_dict(case))
        case.outputs = _output_to_dict(solver.solve())
        db.commit()

    if request.format == "json":
        return Response(
            content=json.dumps({"name": case.name, "inputs": case.inputs, "outputs": case.outputs}, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{case.name}.json"'},
        )
    if request.format == "csv":
        import csv
        import io
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["md_ft", "pressure_psi", "temperature_f", "holdup"])
        for pt in case.outputs.get("well_profile", []):
            writer.writerow([pt["md_ft"], pt["pressure_psi"], pt["temperature_f"], pt["holdup"]])
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{case.name}.csv"'},
        )
    if request.format == "pdf":
        pdf_bytes = generate_pdf_report(case.name, case.inputs, case.outputs)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{case.name}.pdf"'},
        )
    raise HTTPException(400, f"Unsupported format: {request.format}")
