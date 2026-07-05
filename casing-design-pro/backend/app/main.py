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
from engine.benchmarks import run_engine_benchmarks
from engine.montecarlo import run_monte_carlo
from engine.vme import parse_vme_csv_rows

app = FastAPI(title="Casing Design Pro API", version="13.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Casing Design Pro API v13", "docs": "/docs", "status": "ok"}


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "13.0.0", "engine": "python"}


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
    """Run full engine regression benchmarks (parity with JS ENGINE_BENCHMARKS)."""
    return run_engine_benchmarks()
