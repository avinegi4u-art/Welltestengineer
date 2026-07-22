# FlowSim Pro

Steady-state multiphase flow simulation for wells, flowlines, pipelines, and production networks.

**Version 1.1** — Phase A (Beggs-Brill VLP) + Phase B (tubing selector) + Phase C (flowline selector).

## Architecture

```
flowsim-pro/
├── backend/          # FastAPI + Python simulation engine
│   ├── app/          # API routes, database, report generation
│   ├── engine/       # Independent physics modules
│   ├── sample_data/  # Example cases
│   └── tests/        # Unit tests
└── frontend/         # Next.js + React + Tailwind + Plotly
```

### Simulation Engine Modules

| Module | Description |
|--------|-------------|
| `fluid.py` | Black-oil PVT (Standing Bo, Beggs-Robinson viscosity) |
| `beggs_brill.py` | Beggs-Brill (1973) holdup + two-phase friction |
| `well.py` | Tubing VLP with choke orifice ΔP |
| `pipeline.py` | Flowline/pipeline profiles (Beggs-Brill) |
| `nodal.py` | IPR/VLP nodal analysis + sensitivity |
| `catalog.py` | Tubing & flowline size catalogs |
| `selection.py` | Phase B/C tubing & flowline auto-sizing |
| `network.py` | Tree network iterative pressure balance |
| `heat_transfer.py` | Steady-state lumped heat exchange model |
| `solver.py` | Orchestrates end-to-end case solution |

## Quick Start

### Backend

```bash
cd flowsim-pro/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd flowsim-pro/frontend
npm install
npm run dev
```

Open http://localhost:3000

**User manual (PDF):** `flowsim-pro/docs/FlowSim_Pro_User_Manual.pdf` or http://localhost:8000/api/manual

### Run Tests

```bash
cd flowsim-pro/backend
PYTHONPATH=. python -m pytest tests/ -v
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/catalog` | GET | Tubing & flowline size catalogs |
| `/api/cases` | GET/POST | List/create cases |
| `/api/cases/{id}` | GET/PUT/DELETE | Case CRUD |
| `/api/cases/{id}/duplicate` | POST | Duplicate case |
| `/api/solve` | POST | Run simulation |
| `/api/compare` | POST | Compare multiple cases |
| `/api/sensitivity` | POST | Sensitivity analysis |
| `/api/select/tubing` | POST | Phase B tubing catalog sweep |
| `/api/select/flowline` | POST | Phase C flowline diameter sweep |
| `/api/export` | POST | Export PDF/JSON/CSV report |

## Phases

| Phase | Capability |
|-------|------------|
| A | Beggs-Brill VLP, nodal diagnostics, sensitivity overlays |
| B | Tubing catalog auto-sweep, rate/BHP/velocity ranking, API RP 14E erosion screen, Apply ID |
| C | Flowline diameter sweep, ΔP/velocity charts, min-ID recommendation for target ΔP |

## Example Case

See `backend/sample_data/deviated_well_example.json` — a deviated producing well with 3 tubing segments and 2 flowline segments. Expected output ranges are documented in `expected_output.json`.

## Model Assumptions

- **Fluid**: Black-oil with Standing Bo, Beggs-Robinson viscosity, simplified Z-factor
- **Multiphase flow**: Beggs-Brill (tubing + flowline)
- **Choke**: Multiphase orifice; WHP boundary is downstream of choke
- **Heat transfer**: Exponential approach to ambient (lumped UA)
- **IPR**: Linear PI or Vogel correlation
- **Erosion**: API RP 14E `Ve = C / sqrt(ρ)` screening in selectors
- **Units**: Field units (psi, ft, stb/d, °F)

## License

Original engineering software — not affiliated with any commercial flow simulator.
