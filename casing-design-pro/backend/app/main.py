"""Casing Design Pro API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    MonteCarloRequest,
    MonteCarloResponse,
    VmeImportRequest,
    VmeImportResponse,
)
from engine.analyzer import run_analysis
from engine.geometry import pipe_id_from_weight
from engine.loads import cementing_pressure_at_depth, hydrostatic_psi, surge_swab_margin_ppg
from engine.montecarlo import run_monte_carlo
from engine.ratings import (
    api_collapse_pressure,
    barlow_burst,
    body_yield_tension_klbf,
    calc_pipe_ratings,
    sour_derating_factor,
    temp_derating_factor,
)
from engine.vme import parse_vme_csv_rows

app = FastAPI(title="Casing Design Pro API", version="12.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Casing Design Pro API v12", "docs": "/docs"}


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    result = run_analysis(req.model_dump())
    return AnalyzeResponse(**result)


@app.post("/api/montecarlo", response_model=MonteCarloResponse)
def montecarlo(req: MonteCarloRequest):
    result = run_monte_carlo(req.model_dump(), req.iterations)
    return MonteCarloResponse(**result)


@app.post("/api/vme/import", response_model=VmeImportResponse)
def import_vme(req: VmeImportRequest):
    rows = [line.split(",") for line in req.csv_text.strip().splitlines() if line.strip()]
    # handle quoted CSV minimally
    parsed_rows = []
    for line in req.csv_text.strip().splitlines():
        if not line.strip():
            continue
        parsed_rows.append([c.strip().strip('"') for c in line.split(",")])
    curves = parse_vme_csv_rows(parsed_rows)
    return VmeImportResponse(curves=curves, count=len(curves))


@app.get("/api/benchmarks")
def benchmarks():
    """Run engine regression benchmarks."""
    cases = [
        ("barlow_7_23_n80", barlow_burst(7, pipe_id_from_weight(7, 23), 80000), 6444, 2),
        ("hydrostatic_10ppg", hydrostatic_psi(10, 10000), 5200, 0.5),
        ("tension_9_625_p110", body_yield_tension_klbf(9.625, pipe_id_from_weight(9.625, 53.5), 110000), 1513, 3),
        ("collapse_7_23_n80", api_collapse_pressure(7, pipe_id_from_weight(7, 23), 80000), 4402, 3),
        ("temp_derate_p110", temp_derating_factor("P110", 400), 0.9, 2),
        ("sour_derate", sour_derating_factor(0.5), 0.85, 2),
        ("surge_margin", surge_swab_margin_ppg({"pipeSpeedFtMin": 90, "mudPlasticVisc": 25}, True), 0.18, 15),
        ("cement_stage", cementing_pressure_at_depth(5000, [{"topTvd": 0, "bottomTvd": 8000, "densityPpg": 15.5}], 10), 4030, 5),
    ]
    results = []
    for cid, got, expected, tol in cases:
        err = abs(got - expected) / max(abs(expected), 1e-9) * 100
        results.append({"id": cid, "got": got, "expected": expected, "pass": err <= tol})
    return {"benchmarks": results, "pass": sum(1 for r in results if r["pass"]), "total": len(results)}
