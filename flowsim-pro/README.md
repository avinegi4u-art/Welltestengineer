# FlowSim Pro

Steady-state multiphase flow simulation for wells, flowlines, pipelines, and production networks.

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
| `well.py` | Tubing pressure traverse with hydrostatic + friction |
| `pipeline.py` | Flowline/pipeline pressure and temperature profiles |
| `nodal.py` | IPR/VLP nodal analysis with operating point |
| `network.py` | Tree network iterative pressure balance solver |
| `heat_transfer.py` | Steady-state lumped heat exchange model |
| `solver.py` | Orchestrates end-to-end case solution |

## Quick Start

### Backend

```bash
cd flowsim-pro/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd flowsim-pro/frontend
npm install
npm run dev
```

Open http://localhost:3000

### Run Tests

```bash
cd flowsim-pro/backend
pytest tests/ -v
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/cases` | GET/POST | List/create cases |
| `/api/cases/{id}` | GET/PUT/DELETE | Case CRUD |
| `/api/cases/{id}/duplicate` | POST | Duplicate case |
| `/api/solve` | POST | Run simulation |
| `/api/compare` | POST | Compare multiple cases |
| `/api/sensitivity` | POST | Sensitivity analysis |
| `/api/export` | POST | Export PDF/JSON/CSV report |

## Example Case

See `backend/sample_data/deviated_well_example.json` — a deviated producing well with 3 tubing segments and 2 flowline segments. Expected output ranges are documented in `expected_output.json`.

## Model Assumptions

- **Fluid**: Black-oil with Standing Bo, Beggs-Robinson viscosity, simplified Z-factor
- **Multiphase flow**: Drift-flux holdup with Darcy-Weisbach friction (Colebrook-White)
- **Heat transfer**: Exponential approach to ambient (lumped UA)
- **IPR**: Linear PI or Vogel correlation
- **Units**: Field units (psi, ft, stb/d, °F)

## License

Original engineering software — not affiliated with any commercial flow simulator.
