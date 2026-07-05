# Casing Design Pro — Python Engine (v9)

WellCat-class **casing design** screening engine with validated Python backend and browser frontend.

## Architecture

| Layer | Role |
|-------|------|
| `casing-design-pro-v3.html` | Single-file UI (v9) — works offline with embedded JS engine |
| `backend/engine/` | Canonical Python engine — ISO 10400, surge/swab, wear profiles, sour service, probabilistic |
| `backend/app/main.py` | FastAPI — `/api/analyze`, `/api/benchmarks` |

HTML remains the primary interface (no build step). The Python API is optional for heavier runs and regression validation.

## Quick start

### Browser only
Open `casing-design-pro-v3.html` in Chrome/Edge/Firefox.

### With Python API
```bash
chmod +x casing-design-pro/start-backend.sh
./casing-design-pro/start-backend.sh
```
API: http://localhost:8010/docs

In the app, enable **Use Python Engine** on the Project tab (calls `http://localhost:8010/api/analyze`).

### Tests
```bash
cd casing-design-pro/backend
pip install -r requirements.txt
pytest tests/ -v
```

## Phase D — casing gap closure

- **ISO 10400** design code path (distinct burst/collapse factors vs API)
- **Surge / swab** running loads (pipe speed + mud PV)
- **Cementing pressure schedule** (multi-stage density / pressure)
- **Wear vs depth** profiles per string
- **Probabilistic** P90 pore / P10 fracture envelopes
- **Sour service** H₂S partial-pressure derating
- **Hanger / wellhead** axial loads

## vs WellCat

~**92–95%** of casing **design screening** workflow. Not a replacement for Drill-module surge hydraulics, vendor connection databases, or enterprise project management.
