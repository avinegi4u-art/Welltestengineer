"""FlowSim Pro FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routes import router
from engine.solver import SimulationSolver


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    _seed_sample_case()
    yield


def _seed_sample_case():
    """Load example case if database is empty."""
    from app.database import SessionLocal, SimulationCase
    import json
    from pathlib import Path

    db = SessionLocal()
    try:
        if db.query(SimulationCase).count() == 0:
            sample_path = Path(__file__).parent.parent / "sample_data" / "deviated_well_example.json"
            if sample_path.exists():
                with open(sample_path) as f:
                    data = json.load(f)
                case = SimulationCase(
                    name=data.get("case_name", "Deviated Well Example"),
                    description="Sample deviated producing well with tubing and flowline",
                    case_type=data.get("case_type", "well_tubing_flowline"),
                )
                inputs = {k: v for k, v in data.items() if k not in ("case_name", "case_type")}
                case.inputs = inputs
                solver = SimulationSolver(data)
                output = solver.solve()
                case.outputs = {
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
                db.add(case)
                db.commit()
    finally:
        db.close()


app = FastAPI(
    title="FlowSim Pro API",
    description="Steady-state multiphase flow simulation for wells, flowlines, and production networks",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/")
def root():
    return {"message": "FlowSim Pro API", "docs": "/docs"}
