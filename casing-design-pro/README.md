# Casing Design Pro — Python Engine (v11)

WellCat-class **casing design** screening engine with validated Python backend and browser frontend.

## Architecture

| Layer | Role |
|-------|------|
| `casing-design-pro-v3.html` | Single-file UI (v11) — works offline with embedded JS engine |
| `backend/engine/` | Canonical Python engine — full axial/pressure parity with JS (Phase F1) |
| `backend/app/main.py` | FastAPI — `/api/analyze`, `/api/montecarlo`, `/api/benchmarks` |

HTML remains the primary interface (no build step). The Python API is optional; when **Use Python Engine** is enabled, **Run Analysis** and Monte Carlo call the backend.

## Quick start

### Browser only
Open `casing-design-pro-v3.html` in Chrome/Edge/Firefox.

### With Python API

**Important:** Run these in **Command Prompt** or **PowerShell** — not inside the Python `>>>` prompt. If you see `>>>`, type `exit()` first.

**Windows (Command Prompt or PowerShell):**
```bat
cd path\to\Welltestengineer\casing-design-pro\backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload
```
Or double-click / run: `casing-design-pro\start-backend.bat`

**Mac / Linux:**
```bash
chmod +x casing-design-pro/start-backend.sh
./casing-design-pro/start-backend.sh
```

API: http://localhost:8010/docs

In the app, enable **Use Python Engine** on the Project tab — this routes **Run Analysis** and Monte Carlo to `http://localhost:8010`.

### Tests

Run in **Command Prompt / PowerShell / bash** (not the Python `>>>` prompt):

**Windows:**
```bat
cd casing-design-pro\backend
python -m pip install -r requirements.txt
python -m pytest tests/ -v
```

**Mac / Linux:**
```bash
cd casing-design-pro/backend
pip install -r requirements.txt
pytest tests/ -v
```

## Phase F1 — Python engine parity

- **Run Analysis** wired to `POST /api/analyze` when Python engine is on (fallback to local JS)
- Full **axial load** model: buoyed weight, liner/tieback/hanger, thermal, ballooning, packer, running drag
- Full **pressure** model: cemented/open hole, offshore mudline, APB, sealed annuli, fluid segments, thermal scenarios
- **12 new parity tests** in `tests/test_loads_parity.py`

## Phase E — manufacturer VME + Monte Carlo

- **VME CSV import** — test-based burst vs axial curves replace generic ISO ellipse when loaded
- **Monte Carlo** — sample PP/FG/MW uncertainty → P50/P90 utilization + pass probability + histogram
- Python `/api/montecarlo` and `/api/vme/import`
- Sample curve: `sample_data/vam_top_9.625_l80_vme.csv`

## vs WellCat

~**95–98%** of casing **design screening** workflow (JS engine). Python backend now matches JS for axial/pressure loads; buckling/VME-in-Python remain Phase F2.
